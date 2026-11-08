import networkx as nx

def build_graph(records, as_of=None):
    """Evidence-bearing heterogeneous graph; callers must supply a temporal snapshot."""
    g=nx.MultiDiGraph()
    def node(identifier,kind,t):
        first=g.nodes[identifier]['first_observed_at'] if identifier in g else str(t['timestamp'])
        g.add_node(identifier,id=identifier,type=kind,source=t['source'],first_observed_at=min(first,str(t['timestamp'])))
    def edge(a,b,kind,t):
        key=f"{t['id']}:{kind}"
        g.add_edge(a,b,key=key,id=key,source=a,target=b,type=kind,timestamp=str(t['timestamp']),
            amount=t['amount'],evidence_reference=t['id'],provenance=t['source'])
    for t in records:
        if as_of and str(t['timestamp'])>as_of: continue
        a,b,tx='account:'+t['account_id'],'account:'+t['beneficiary_id'],'transaction:'+t['id']
        customer='customer:'+t['account_id']
        for identifier,kind in [(a,'account'),(b,'account'),(tx,'transaction')]: node(identifier,kind,t)
        if t.get('synthetic'):
            node(customer,'customer',t); edge(customer,a,'OWNS_ACCOUNT',t)
        edge(a,tx,'INITIATED_TRANSACTION',t); edge(tx,b,'RECEIVED_TRANSACTION',t); edge(a,b,'TRANSFERRED_TO',t)
        beneficiary='beneficiary:'+t['beneficiary_id']; node(beneficiary,'beneficiary',t); edge(b,beneficiary,'LINKED_TO_ACCOUNT',t)
        if t.get('device_id'):
            d='device:'+t['device_id']; node(d,'device',t); edge(a,d,'USES_DEVICE',t)
        if t.get('merchant_id'):
            m='merchant:'+t['merchant_id']; node(m,'merchant',t); edge(tx,m,'TRANSACTED_WITH_MERCHANT',t)
    return g

def account_graph(g):
    projected=nx.DiGraph()
    for a,b,d in g.edges(data=True):
        if d['type']=='TRANSFERRED_TO':
            if projected.has_edge(a,b): projected[a][b]['weight']+=1
            else: projected.add_edge(a,b,weight=1)
    return projected

def metrics(g):
    p=account_graph(g)
    if not p: return dict(nodes=g.number_of_nodes(),edges=g.number_of_edges(),accounts=0,communities=[],components=0,degree={},pagerank={},betweenness={})
    undirected=p.to_undirected()
    communities=list(nx.community.greedy_modularity_communities(undirected,weight='weight')) if undirected.number_of_edges() else [{n} for n in p]
    return dict(nodes=g.number_of_nodes(),edges=g.number_of_edges(),accounts=len(p),
        communities=[sorted(c) for c in communities],components=nx.number_connected_components(undirected),
        degree=nx.degree_centrality(p),pagerank=nx.pagerank(p),
        betweenness=nx.betweenness_centrality(p,k=min(len(p),40),seed=42))

def neighborhood(g,node,hops=1,limit=180):
    if node not in g: return {'nodes':[],'edges':[],'truncated':False}
    paths=nx.single_source_shortest_path_length(g.to_undirected(),node,cutoff=hops)
    selected=sorted(paths,key=lambda n:(paths[n],n))[:limit]
    sub=g.subgraph(selected)
    return {'nodes':[d for _,d in sub.nodes(data=True)],'edges':[d for *_,d in sub.edges(data=True)],'truncated':len(paths)>limit}

def persist(db,g):
    import hashlib
    from ..database import GraphEntity, GraphRelationship
    from sqlalchemy import delete
    db.execute(delete(GraphRelationship)); db.execute(delete(GraphEntity))
    for n,d in g.nodes(data=True): db.add(GraphEntity(id=n,payload=d))
    db.flush()
    for a,b,key,d in g.edges(keys=True,data=True): db.add(GraphRelationship(id=hashlib.sha256(f'{a}:{key}'.encode()).hexdigest(),source_id=a,target_id=b,payload=d))
    db.flush()
