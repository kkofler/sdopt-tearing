"""
*****
Pydot
*****

Import and export NetworkX graphs in Graphviz dot format using pydotplus.

Either this module or nx_agraph can be used to interface with graphviz.

See Also
--------
PyDotPlus: https://github.com/carlos-jenkins/pydotplus
Graphviz:          http://www.research.att.com/sw/tools/graphviz/
DOT Language:  http://www.graphviz.org/doc/info/lang.html
"""
# Author: Aric Hagberg (aric.hagberg@gmail.com)

#    Copyright (C) 2004-2016 by
#    Aric Hagberg <hagberg@lanl.gov>
#    Dan Schult <dschult@colgate.edu>
#    Pieter Swart <swart@lanl.gov>
#    All rights reserved.
#    BSD license.
import importlib
from networkx.utils import open_file, make_str
import networkx as nx

__all__ = ['write_dot', 'read_dot', 'graphviz_layout', 'pydot_layout',
           'to_pydot', 'from_pydot']

# 2.x/3.x compatibility
try:
    basestring
except NameError:
    basestring = str

@open_file(1, mode='w')
def write_dot(G, path):
    """Write NetworkX graph G to Graphviz dot format on path.

    Path can be a string or a file handle.
    """
    P=to_pydot(G)
    path.write(P.to_string())
    return

@open_file(0, mode='r')
def read_dot(path):
    """Return a NetworkX MultiGraph or MultiDiGraph from a dot file on path.

    Parameters
    ----------
    path : filename or file handle

    Returns
    -------
    G : NetworkX multigraph
        A MultiGraph or MultiDiGraph.

    Notes
    -----
    Use G = nx.Graph(read_dot(path)) to return a Graph instead of a MultiGraph.
    """
    import pydotplus
    data = path.read()
    P = pydotplus.graph_from_dot_data(data)
    return from_pydot(P)

def from_pydot(P):
    """Return a NetworkX graph from a Pydot graph.

    Parameters
    ----------
    P : Pydot graph
      A graph created with Pydot

    Returns
    -------
    G : NetworkX multigraph
        A MultiGraph or MultiDiGraph.

    Examples
    --------
    >>> K5 = nx.complete_graph(5)
    >>> A = nx.nx_pydot.to_pydot(K5)
    >>> G = nx.nx_pydot.from_pydot(A) # return MultiGraph

    # make a Graph instead of MultiGraph
    >>> G = nx.Graph(nx.nx_pydot.from_pydot(A)) 

    """
    if P.get_strict(None): # pydot bug: get_strict() shouldn't take argument
        multiedges=False
    else:
        multiedges=True

    if P.get_type()=='graph': # undirected
        if multiedges:
            N = nx.MultiGraph()
        else:
            N = nx.Graph()
    else:
        if multiedges:
            N = nx.MultiDiGraph()
        else:
            N = nx.DiGraph()

    # assign defaults
    name=P.get_name().strip('"')
    if name != '':
        N.name = name

    # add nodes, attributes to N.node_attr
    for p in P.get_node_list():
        n=p.get_name().strip('"')
        if n in ('node','graph','edge'):
            continue
        N.add_node(n,**p.get_attributes())

    # add edges
    for e in P.get_edge_list():
        u=e.get_source()
        v=e.get_destination()
        attr=e.get_attributes()
        s=[]
        d=[]

        if isinstance(u, basestring):
            s.append(u.strip('"'))
        else:
            for unodes in u['nodes']:
                s.append(unodes.strip('"'))

        if isinstance(v, basestring):
            d.append(v.strip('"'))
        else:
            for vnodes in v['nodes']:
                d.append(vnodes.strip('"'))

        for source_node in s:
            for destination_node in d:
                N.add_edge(source_node,destination_node,**attr)

    # add default attributes for graph, nodes, edges
    pattr = P.get_attributes()
    if pattr:
        N.graph['graph'] = pattr
    try:
        N.graph['node']=P.get_node_defaults()[0]
    except:# IndexError,TypeError:
        pass #N.graph['node']={}
    try:
        N.graph['edge']=P.get_edge_defaults()[0]
    except:# IndexError,TypeError:
        pass #N.graph['edge']={}
    return N

def to_pydot(N, strict=True):
    """Return a pydot graph from a NetworkX graph N.

    Parameters
    ----------
    N : NetworkX graph
      A graph created with NetworkX

    Examples
    --------
    >>> K5 = nx.complete_graph(5)
    >>> P = nx.nx_pydot.to_pydot(K5)

    Notes
    -----

    """
    import pydotplus
    # set Graphviz graph type
    if N.is_directed():
        graph_type='digraph'
    else:
        graph_type='graph'
    strict=N.number_of_selfloops()==0 and not N.is_multigraph()

    name = N.name
    graph_defaults=N.graph.get('graph',{})
    if name == '':
        P = pydotplus.Dot('', graph_type=graph_type, strict=strict,
                      **graph_defaults)
    else:
        P = pydotplus.Dot('"%s"'%name, graph_type=graph_type, strict=strict,
                      **graph_defaults)
    try:
        P.set_node_defaults(**N.graph['node'])
    except KeyError:
        pass
    try:
        P.set_edge_defaults(**N.graph['edge'])
    except KeyError:
        pass

    for n,nodedata in N.nodes_iter(data=True):
        str_nodedata=dict((k,make_str(v)) for k,v in nodedata.items())
        p=pydotplus.Node(make_str(n),**str_nodedata)
        P.add_node(p)

    if N.is_multigraph():
        for u,v,key,edgedata in N.edges_iter(data=True,keys=True):
            str_edgedata=dict((k,make_str(v)) for k,v in edgedata.items())
            edge=pydotplus.Edge(make_str(u), make_str(v),
                    key=make_str(key), **str_edgedata)
            P.add_edge(edge)

    else:
        for u,v,edgedata in N.edges_iter(data=True):
            str_edgedata=dict((k,make_str(v)) for k,v in edgedata.items())
            edge=pydotplus.Edge(make_str(u),make_str(v),**str_edgedata)
            P.add_edge(edge)
    return P


def pydot_from_networkx(N):
    """Create a Pydot graph from a NetworkX graph."""
    from warnings import warn
    warn('pydot_from_networkx is replaced by to_pydot', DeprecationWarning)
    return to_pydot(N)

def networkx_from_pydot(D, create_using=None):
    """Create a NetworkX graph from a Pydot graph."""
    from warnings import warn
    warn('networkx_from_pydot is replaced by from_pydot',
         DeprecationWarning)
    return from_pydot(D)

def graphviz_layout(G,prog='neato',root=None, **kwds):
    """Create node positions using Pydot and Graphviz.

    Returns a dictionary of positions keyed by node.

    Examples
    --------
    >>> G = nx.complete_graph(4)
    >>> pos = nx.nx_pydot.graphviz_layout(G)
    >>> pos = nx.nx_pydot.graphviz_layout(G, prog='dot')

    Notes
    -----
    This is a wrapper for pydot_layout.
    """
    return pydot_layout(G=G,prog=prog,root=root,**kwds)


def pydot_layout(G,prog='neato',root=None, **kwds):
    """Create node positions using Pydot and Graphviz.

    Returns a dictionary of positions keyed by node.

    Examples
    --------
    >>> G = nx.complete_graph(4)
    >>> pos = nx.nx_pydot.pydot_layout(G)
    >>> pos = nx.nx_pydot.pydot_layout(G, prog='dot')
    """
    import pydotplus
    P=to_pydot(G)
    if root is not None :
        P.set("root",make_str(root))

    D=P.create_dot(prog=prog)

    if D=="":  # no data returned
        print("Graphviz layout with %s failed"%(prog))
        print()
        print("To debug what happened try:")
        print("P=pydot_from_networkx(G)")
        print("P.write_dot(\"file.dot\")")
        print("And then run %s on file.dot"%(prog))
        return

    Q=pydotplus.graph_from_dot_data(D)

    node_pos={}
    for n in G.nodes():
        pydot_node = pydotplus.Node(make_str(n)).get_name()
        node=Q.get_node(pydot_node)

        if isinstance(node,list):
            node=node[0]
        pos=node.get_pos()[1:-1] # strip leading and trailing double quotes
        if pos != None:
            xx,yy=pos.split(",")
            node_pos[n]=(float(xx),float(yy))
    return node_pos

# fixture for nose tests
def setup_module(module):
    from nose import SkipTest
    try:
        import pydotplus
    except ImportError:
        raise SkipTest("pydotplus not available")
