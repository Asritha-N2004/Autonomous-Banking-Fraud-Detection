from concurrent.futures import ThreadPoolExecutor, wait
from time import perf_counter
from typing import TypedDict
from ..schemas import AgentResult
from .specialists import SPECIALISTS

class InvestigationState(TypedDict):
    phase: str
    results: dict
    logs: list
    errors: list
    iterations: int

class Supervisor:
    """Explicit bounded hierarchical state machine; tools only receive immutable snapshots."""
    parallel=('transaction','behavioral','account','graph','ml','pattern')
    sequential=('evidence','risk','investigation','compliance','reporting')

    def run(self,ctx,disabled=()):
        start=perf_counter(); settings=ctx['settings']
        deadline=start+settings['investigation_timeout_seconds']
        state: InvestigationState={'phase':'supervisor_dispatch','results':{},'logs':[],'errors':[],'iterations':0}
        def execute(name,snapshot):
            errors=[]; began=perf_counter()
            for attempt in range(min(settings['max_iterations'],settings['agent_retries']+1)):
                if perf_counter()>deadline: break
                try:
                    output=AgentResult.model_validate(SPECIALISTS[name](ctx,snapshot)).model_dump()
                    if output['agent']!=name: raise ValueError('Agent identity mismatch')
                    known={t['id'] for t in ctx['prior']}|{ctx['transaction']['id']}
                    if not output['references'] or not set(output['references'])<=known: raise ValueError('Invalid evidence references')
                    if not output['provenance'] or not output['uncertainty']: raise ValueError('Missing provenance or uncertainty')
                    return output,{'agent':name,'status':'completed','attempts':attempt+1,'duration_ms':(perf_counter()-began)*1000,
                        'input_summary':{'transaction_id':ctx['transaction']['id'],'dependencies':list(snapshot)},'output':output,'errors':errors}
                except Exception as exc: errors.append(type(exc).__name__+': '+str(exc))
            return None,{'agent':name,'status':'failed','attempts':len(errors),'duration_ms':(perf_counter()-began)*1000,'errors':errors or ['Investigation timeout']}
        pool=ThreadPoolExecutor(max_workers=6)
        jobs={pool.submit(execute,name,{}):name for name in self.parallel if name not in disabled}
        done,pending=wait(jobs,timeout=max(.001,deadline-perf_counter()))
        for future in done:
            output,log=future.result(); state['logs'].append(log)
            if output: state['results'][jobs[future]]=output
            else: state['errors'].append(jobs[future])
        for future in pending:
            future.cancel(); state['errors'].append(jobs[future]); state['logs'].append({'agent':jobs[future],'status':'timeout','attempts':0,'duration_ms':settings['investigation_timeout_seconds']*1000})
        pool.shutdown(wait=False,cancel_futures=True)
        state['phase']='dependent_investigation'
        for name in self.sequential:
            if name in disabled: continue
            output,log=execute(name,dict(state['results'])); state['logs'].append(log)
            if output: state['results'][name]=output
            else: state['errors'].append(name)
            if name in ['evidence','risk'] and not output: break
        state['iterations']=max((l.get('attempts',0) for l in state['logs']),default=0)
        state['phase']='human_review_checkpoint' if 'reporting' in state['results'] else 'incomplete'
        state['duration_ms']=(perf_counter()-start)*1000
        state['supervisor_review']={'evidence_validated':True,'incomplete_agents':state['errors'],'human_review_required':True,
            'consequential_actions_executed':False}
        return state
