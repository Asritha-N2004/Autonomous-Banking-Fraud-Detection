// All API responses here are explicitly synthetic fixtures; production uses live APIs.
import { describe,it,expect,vi,afterEach } from 'vitest'
import { render,screen,fireEvent,waitFor,cleanup } from '@testing-library/react'
import '@testing-library/jest-dom/vitest'
import App from './App'
vi.mock('recharts',()=>({ResponsiveContainer:({children}:any)=><div>{children}</div>,AreaChart:()=>null,Area:()=>null,XAxis:()=>null,YAxis:()=>null,Tooltip:()=>null,CartesianGrid:()=>null,BarChart:()=>null,Bar:()=>null}))
vi.mock('@xyflow/react',()=>({ReactFlow:()=> <div>Interactive graph fixture</div>,Background:()=>null,Controls:()=>null,MiniMap:()=>null}))
afterEach(()=>{cleanup();vi.restoreAllMocks()})
const syntheticCase={id:'synthetic-case',transaction_id:'SYN-T000001',priority:60,category:'high',status:'awaiting_review',created_at:'2025-01-01T00:00:00Z',assigned_to:'synthetic-admin'}
const syntheticEvidence={id:'synthetic-evidence',payload:{type:'graph',description:'Synthetic device relationship',timestamp:'2025-01-01',references:['SYN-T000001'],quality:.75,provenance:{source:'synthetic-fixture'}}}
function mock(role='ADMIN',failedPath?:string){
 vi.stubGlobal('fetch',vi.fn(async(input:string)=>{
 const path=String(input).replace('/api','').split('?')[0]
 if(path===failedPath)return {ok:false,json:async()=>({detail:'Synthetic temporary server failure'})}
 const data:Record<string,unknown>={
 '/auth/me':{username:'synthetic-admin',id:'synthetic-admin',role},'/analytics/dashboard':{total_transactions:123,analyzed_transactions:4,alerts:2,open_investigations:1,high_priority_cases:1,model_available:true},
 '/analytics/transaction-trends':{items:[]},'/fraud/alerts':{items:[{id:'synthetic-alert',transaction_id:'SYN-T000001',priority:60,category:'high',status:'unverified',case_id:'synthetic-case'}]},
 '/models/metrics':{seed:42,metrics:{random_forest:{precision:.8,recall:.7,pr_auc:.6}},splits:{test:100}},'/analytics/agent-performance':{items:[]},
 '/investigations':{items:[syntheticCase]},'/transactions':{total:1,items:[{id:'SYN-T000001',account_id:'SYN-A001',timestamp:'2025-01-01',amount:1234,channel:'web',review_status:'not_analyzed'}]},
 '/graph/neighborhood/account%3ASYN-A000':{nodes:[],edges:[]},'/evidence':{total:1,items:[syntheticEvidence]},
 '/agents/runs':{items:[{id:'synthetic-run',duration_ms:12,status:'awaiting_human_review'}]},'/agents/logs/synthetic-run':{items:[{id:'synthetic-log',agent:'graph',payload:{status:'completed',duration_ms:4,attempts:1}}]}}
 return {ok:true,json:async()=>data[path]??{items:[]}}
 }))
}
describe('Synthetic dashboard integration fixtures',()=>{
 it('keeps successful dashboard data when a trend request fails',async()=>{mock('ADMIN','/analytics/transaction-trends');render(<App/>);expect(await screen.findByText('123')).toBeInTheDocument();expect(await screen.findByRole('alert')).toHaveTextContent('Transaction activity could not be loaded');expect(screen.getByText('0.600')).toBeInTheDocument()})
 it('renders backend dashboard values',async()=>{mock();render(<App/>);expect(await screen.findByText('123')).toBeInTheDocument();expect(screen.getByRole('heading',{name:'Investigation overview'})).toBeInTheDocument()})
 it('opens transaction monitoring with API records',async()=>{mock();render(<App/>);await screen.findByText('123');fireEvent.click(screen.getByRole('button',{name:'Transactions'}));expect(await screen.findByText('SYN-A001')).toBeInTheDocument();expect(screen.getByRole('button',{name:/Investigate/})).toBeInTheDocument()})
 it('renders ranked unverified alerts',async()=>{mock();render(<App/>);await screen.findByText('123');fireEvent.click(screen.getByRole('button',{name:/Detection results/}));expect(await screen.findByRole('heading',{name:'Ranked investigation alerts'})).toBeInTheDocument();expect(screen.getByText('unverified')).toBeInTheDocument()})
 it('loads graph explorer and relationship inspector',async()=>{mock();render(<App/>);await screen.findByText('123');fireEvent.click(screen.getByRole('button',{name:'Graph explorer'}));expect(await screen.findByText('Interactive graph fixture')).toBeInTheDocument();expect(screen.getByText('Relationship inspector')).toBeInTheDocument()})
 it('renders case management',async()=>{mock();render(<App/>);await screen.findByText('123');fireEvent.click(screen.getByRole('button',{name:'Investigations'}));expect(await screen.findByRole('heading',{name:'Case management'})).toBeInTheDocument();expect(screen.getByText('SYN-T000001')).toBeInTheDocument()})
 it('renders evidence and its references',async()=>{mock();render(<App/>);await screen.findByText('123');fireEvent.click(screen.getByRole('button',{name:'Evidence'}));expect(await screen.findByText('Synthetic device relationship')).toBeInTheDocument();expect(screen.getByText('SYN-T000001')).toBeInTheDocument()})
 it('renders agent execution trace',async()=>{mock();render(<App/>);await screen.findByText('123');fireEvent.click(screen.getByRole('button',{name:'Agent monitor'}));expect(await screen.findByText('completed')).toBeInTheDocument();expect(screen.getByText('graph')).toBeInTheDocument()})
 it('hides restricted pages for analysts',async()=>{mock('ANALYST');render(<App/>);await screen.findByText('123');expect(screen.queryByRole('button',{name:'Settings'})).not.toBeInTheDocument();expect(screen.queryByRole('button',{name:'Reports'})).not.toBeInTheDocument()})
 it('shows login when unauthenticated',async()=>{vi.stubGlobal('fetch',vi.fn(async()=>({ok:false,json:async()=>({detail:'Authentication required'})})));render(<App/>);expect(await screen.findByRole('button',{name:/Sign in to workspace/})).toBeInTheDocument()})
})
