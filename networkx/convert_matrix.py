"""Functions to convert NetworkX graphs to and from numpy/scipy matrices.

The preferred way of converting data to a NetworkX graph is through the
graph constuctor.  The constructor calls the to_networkx_graph() function
which attempts to guess the input type and convert it automatically.

Examples
--------
Create a 10 node random graph from a numpy matrix

>>> import numpy
>>> a = numpy.reshape(numpy.random.random_integers(0,1,size=100),(10,10))
>>> D = nx.DiGraph(a)

or equivalently

>>> D = nx.to_networkx_graph(a,create_using=nx.DiGraph())

See Also
--------
nx_agraph, nx_pydot
"""
#    Copyright (C) 2006-2014 by
#    Aric Hagberg <hagberg@lanl.gov>
#    Dan Schult <dschult@colgate.edu>
#    Pieter Swart <swart@lanl.gov>
#    All rights reserved.
#    BSD license.
import warnings
import itertools
import networkx as nx
from networkx.convert import _prep_create_using
from networkx.utils import not_implemented_for
__author__ = """\n""".join(['Aric Hagberg <aric.hagberg@gmail.com>',
                           'Pieter Swart (swart@lanl.gov)',
                           'Dan Schult(dschult@colgate.edu)'])
__all__ = ['from_numpy_matrix', 'to_numpy_matrix',
           'from_pandas_dataframe', 'to_pandas_dataframe',
           'to_numpy_recarray',
           'from_scipy_sparse_matrix', 'to_scipy_sparse_matrix']

def to_pandas_dataframe(G, nodelist=None, multigraph_weight=sum, weight='weight', nonedge=0.0):
    """Return the graph adjacency matrix as a Pandas DataFrame.

    Parameters
    ----------
    G : graph
        The NetworkX graph used to construct the Pandas DataFrame.

    nodelist : list, optional
       The rows and columns are ordered according to the nodes in `nodelist`.
       If `nodelist` is None, then the ordering is produced by G.nodes().

    multigraph_weight : {sum, min, max}, optional
        An operator that determines how weights in multigraphs are handled.
        The default is to sum the weights of the multiple edges.

    weight : string or None, optional
        The edge attribute that holds the numerical value used for
        the edge weight.  If an edge does not have that attribute, then the
        value 1 is used instead.

    nonedge : float, optional
        The matrix values corresponding to nonedges are typically set to zero.
        However, this could be undesirable if there are matrix values
        corresponding to actual edges that also have the value zero. If so,
        one might prefer nonedges to have some other value, such as nan.

    Returns
    -------
    df : Pandas DataFrame
       Graph adjacency matrix

    Notes
    -----
    The DataFrame entries are assigned to the weight edge attribute. When
    an edge does not have a weight attribute, the value of the entry is set to
    the number 1.  For multiple (parallel) edges, the values of the entries
    are determined by the 'multigraph_weight' parameter.  The default is to
    sum the weight attributes for each of the parallel edges.

    When `nodelist` does not contain every node in `G`, the matrix is built
    from the subgraph of `G` that is induced by the nodes in `nodelist`.

    The convention used for self-loop edges in graphs is to assign the
    diagonal matrix entry value to the weight attribute of the edge
    (or the number 1 if the edge has no weight attribute).  If the
    alternate convention of doubling the edge weight is desired the
    resulting Pandas DataFrame can be modified as follows:

    >>> import pandas as pd
    >>> import numpy as np
    >>> G = nx.Graph([(1,1)])
    >>> df = nx.to_pandas_dataframe(G)
    >>> df
       1
    1  1
    >>> df.values[np.diag_indices_from(df)] *= 2
    >>> df
       1
    1  2

    Examples
    --------
    >>> G = nx.MultiDiGraph()
    >>> G.add_edge(0,1,weight=2)
    >>> G.add_edge(1,0)
    >>> G.add_edge(2,2,weight=3)
    >>> G.add_edge(2,2)
    >>> nx.to_pandas_dataframe(G, nodelist=[0,1,2])
       0  1  2
    0  0  2  0
    1  1  0  0
    2  0  0  4
    """
    import pandas as pd
    M = to_numpy_matrix(G, nodelist, None, None, multigraph_weight, weight, nonedge)
    if nodelist is None:
        nodelist = G.nodes()
    nodeset = set(nodelist)
    df = pd.DataFrame(data=M, index = nodelist ,columns = nodelist)
    return df

def from_pandas_dataframe(df, source, target, edge_attr=None,
        create_using=None):
    """Return a graph from Pandas DataFrame.

    The Pandas DataFrame should contain at least two columns of node names and
    zero or more columns of node attributes. Each row will be processed as one
    edge instance.

    Note: This function iterates over DataFrame.values, which is not
    guaranteed to retain the data type across columns in the row. This is only
    a problem if your row is entirely numeric and a mix of ints and floats. In
    that case, all values will be returned as floats. See the
    DataFrame.iterrows documentation for an example.

    Parameters
    ----------
    df : Pandas DataFrame
        An edge list representation of a graph

    source : str or int
        A valid column name (string or iteger) for the source nodes (for the
        directed case).

    target : str or int
        A valid column name (string or iteger) for the target nodes (for the
        directed case).

    edge_attr : str or int, iterable, True
        A valid column name (str or integer) or list of column names that will
        be used to retrieve items from the row and add them to the graph as edge
        attributes. If `True`, all of the remaining columns will be added.

    create_using : NetworkX graph
        Use specified graph for result.  The default is Graph()

    See Also
    --------
    to_pandas_dataframe

    Examples
    --------
    Simple integer weights on edges:

    >>> import pandas as pd
    >>> import numpy as np
    >>> r = np.random.RandomState(seed=5)
    >>> ints = r.random_integers(1, 10, size=(3,2))
    >>> a = ['A', 'B', 'C']
    >>> b = ['D', 'A', 'E']
    >>> df = pd.DataFrame(ints, columns=['weight', 'cost'])
    >>> df[0] = a
    >>> df['b'] = b
    >>> df
       weight  cost  0  b
    0       4     7  A  D
    1       7     1  B  A
    2      10     9  C  E
    >>> G=nx.from_pandas_dataframe(df, 0, 'b', ['weight', 'cost'])
    >>> G['E']['C']['weight']
    10
    >>> G['E']['C']['cost']
    9
    """

    g = _prep_create_using(create_using)

    # Index of source and target
    src_i = df.columns.get_loc(source)
    tar_i = df.columns.get_loc(target)
    if edge_attr:
        # If all additional columns requested, build up a list of tuples
        # [(name, index),...]
        if edge_attr is True:
            # Create a list of all columns indices, ignore nodes
            edge_i = []
            for i, col in enumerate(df.columns):
                if col is not source and col is not target:
                    edge_i.append((col, i))
        # If a list or tuple of name is requested
        elif isinstance(edge_attr, (list, tuple)):
            edge_i = [(i, df.columns.get_loc(i)) for i in edge_attr]
        # If a string or int is passed
        else:
            edge_i = [(edge_attr, df.columns.get_loc(edge_attr)),]

        # Iteration on values returns the rows as Numpy arrays
        for row in df.values:
            g.add_edge(row[src_i], row[tar_i], {i:row[j] for i, j in edge_i})
    
    # If no column names are given, then just return the edges.
    else:
        for row in df.values:
            g.add_edge(row[src_i], row[tar_i])

    return g

def to_numpy_matrix(G, nodelist=None, dtype=None, order=None,
                    multigraph_weight=sum, weight='weight', nonedge=0.0):
    """Return the graph adjacency matrix as a NumPy matrix.

    Parameters
    ----------
    G : graph
        The NetworkX graph used to construct the NumPy matrix.

    nodelist : list, optional
        The rows and columns are ordered according to the nodes in ``nodelist``.
        If ``nodelist`` is None, then the ordering is produced by G.nodes().

    dtype : NumPy data type, optional
        A valid single NumPy data type used to initialize the array.
        This must be a simple type such as int or numpy.float64 and
        not a compound data type (see to_numpy_recarray)
        If None, then the NumPy default is used.

    order : {'C', 'F'}, optional
        Whether to store multidimensional data in C- or Fortran-contiguous
        (row- or column-wise) order in memory. If None, then the NumPy default
        is used.

    multigraph_weight : {sum, min, max}, optional
        An operator that determines how weights in multigraphs are handled.
        The default is to sum the weights of the multiple edges.

    weight : string or None optional (default = 'weight')
        The edge attribute that holds the numerical value used for
        the edge weight. If an edge does not have that attribute, then the
        value 1 is used instead.

    nonedge : float (default = 0.0)
        The matrix values corresponding to nonedges are typically set to zero.
        However, this could be undesirable if there are matrix values
        corresponding to actual edges that also have the value zero. If so,
        one might prefer nonedges to have some other value, such as nan.

    Returns
    -------
    M : NumPy matrix
        Graph adjacency matrix

    See Also
    --------
    to_numpy_recarray, from_numpy_matrix

    Notes
    -----
    The matrix entries are assigned to the weight edge attribute. When
    an edge does not have a weight attribute, the value of the entry is set to
    the number 1.  For multiple (parallel) edges, the values of the entries
    are determined by the ``multigraph_weight`` parameter.  The default is to
    sum the weight attributes for each of the parallel edges.

    When ``nodelist`` does not contain every node in ``G``, the matrix is built
    from the subgraph of ``G`` that is induced by the nodes in ``nodelist``.

    The convention used for self-loop edges in graphs is to assign the
    diagonal matrix entry value to the weight attribute of the edge
    (or the number 1 if the edge has no weight attribute).  If the
    alternate convention of doubling the edge weight is desired the
    resulting Numpy matrix can be modified as follows:

    >>> import numpy as np
    >>> G = nx.Graph([(1, 1)])
    >>> A = nx.to_numpy_matrix(G)
    >>> A
    matrix([[ 1.]])
    >>> A.A[np.diag_indices_from(A)] *= 2
    >>> A
    matrix([[ 2.]])

    Examples
    --------
    >>> G = nx.MultiDiGraph()
    >>> G.add_edge(0,1,weight=2)
    >>> G.add_edge(1,0)
    >>> G.add_edge(2,2,weight=3)
    >>> G.add_edge(2,2)
    >>> nx.to_numpy_matrix(G, nodelist=[0,1,2])
    matrix([[ 0.,  2.,  0.],
            [ 1.,  0.,  0.],
            [ 0.,  0.,  4.]])
    """
    import numpy as np
    if nodelist is None:
        nodelist = G.nodes()
    nodeset = set(nodelist)
    if len(nodelist) != len(nodeset):
        msg = "Ambiguous ordering: `nodelist` contained duplicates."
        raise nx.NetworkXError(msg)

    nlen=len(nodelist)
    undirected = not G.is_directed()
    index=dict(zip(nodelist,range(nlen)))

    # Initially, we start with an array of nans.  Then we populate the matrix
    # using data from the graph.  Afterwards, any leftover nans will be
    # converted to the value of `nonedge`.  Note, we use nans initially,
    # instead of zero, for two reasons:
    #
    #   1) It can be important to distinguish a real edge with the value 0
    #      from a nonedge with the value 0.
    #
    #   2) When working with multi(di)graphs, we must combine the values of all
    #      edges between any two nodes in some manner.  This often takes the
    #      form of a sum, min, or max.  Using the value 0 for a nonedge would
    #      have undesirable effects with min and max, but using nanmin and
    #      nanmax with initially nan values is not problematic at all.
    #
    # That said, there are still some drawbacks to this approach. Namely, if
    # a real edge is nan, then that value is a) not distinguishable from
    # nonedges and b) is ignored by the default combinator (nansum, nanmin,
    # nanmax) functions used for multi(di)graphs. If this becomes an issue,
    # an alternative approach is to use masked arrays.  Initially, every
    # element is masked and set to some `initial` value. As we populate the
    # graph, elements are unmasked (automatically) when we combine the initial
    # value with the values given by real edges.  At the end, we convert all
    # masked values to `nonedge`. Using masked arrays fully addresses reason 1,
    # but for reason 2, we would still have the issue with min and max if the
    # initial values were 0.0.  Note: an initial value of +inf is appropriate
    # for min, while an initial value of -inf is appropriate for max. When
    # working with sum, an initial value of zero is appropriate. Ideally then,
    # we'd want to allow users to specify both a value for nonedges and also
    # an initial value.  For multi(di)graphs, the choice of the initial value
    # will, in general, depend on the combinator function---sensible defaults
    # can be provided.

    if G.is_multigraph():
        # Handle MultiGraphs and MultiDiGraphs
        M = np.zeros((nlen, nlen), dtype=dtype, order=order) + np.nan
        # use numpy nan-aware operations
        operator={sum:np.nansum, min:np.nanmin, max:np.nanmax}
        try:
            op=operator[multigraph_weight]
        except:
            raise ValueError('multigraph_weight must be sum, min, or max')

        for u,v,attrs in G.edges_iter(data=True):
            if (u in nodeset) and (v in nodeset):
                i, j = index[u], index[v]
                e_weight = attrs.get(weight, 1)
                M[i,j] = op([e_weight, M[i,j]])
                if undirected:
                    M[j,i] = M[i,j]
    else:
        # Graph or DiGraph, this is much faster than above
        M = np.zeros((nlen,nlen), dtype=dtype, order=order) + np.nan
        for u,nbrdict in G.adjacency_iter():
            for v,d in nbrdict.items():
                try:
                    M[index[u],index[v]] = d.get(weight,1)
                except KeyError:
                    # This occurs when there are fewer desired nodes than
                    # there are nodes in the graph: len(nodelist) < len(G)
                    pass

    M[np.isnan(M)] = nonedge
    M = np.asmatrix(M)
    return M


def from_numpy_matrix(A, parallel_edges=False, create_using=None):
    """Return a graph from numpy matrix.

    The numpy matrix is interpreted as an adjacency matrix for the graph.

    Parameters
    ----------
    A : numpy matrix
        An adjacency matrix representation of a graph

    parallel_edges : Boolean
        If this is ``True``, ``create_using`` is a multigraph, and ``A`` is an
        integer matrix, then entry *(i, j)* in the matrix is interpreted as the
        number of parallel edges joining vertices *i* and *j* in the graph. If it
        is ``False``, then the entries in the adjacency matrix are interpreted as
        the weight of a single edge joining the vertices.

    create_using : NetworkX graph
        Use specified graph for result. The default is Graph()

    Notes
    -----
    If ``create_using`` is an instance of :class:`networkx.MultiGraph` or
    :class:`networkx.MultiDiGraph`, ``parallel_edges`` is ``True``, and the
    entries of ``A`` are of type ``int``, then this function returns a multigraph
    (of the same type as ``create_using``) with parallel edges.

    If ``create_using`` is an undirected multigraph, then only the edges
    indicated by the upper triangle of the matrix `A` will be added to the
    graph.

    If the numpy matrix has a single data type for each matrix entry it
    will be converted to an appropriate Python data type.

    If the numpy matrix has a user-specified compound data type the names
    of the data fields will be used as attribute keys in the resulting
    NetworkX graph.

    See Also
    --------
    to_numpy_matrix, to_numpy_recarray

    Examples
    --------
    Simple integer weights on edges:

    >>> import numpy
    >>> A=numpy.matrix([[1, 1], [2, 1]])
    >>> G=nx.from_numpy_matrix(A)

    If ``create_using`` is a multigraph and the matrix has only integer entries,
    the entries will be interpreted as weighted edges joining the vertices
    (without creating parallel edges):

    >>> import numpy
    >>> A = numpy.matrix([[1, 1], [1, 2]])
    >>> G = nx.from_numpy_matrix(A, create_using = nx.MultiGraph())
    >>> G[1][1]
    {0: {'weight': 2}}

    If ``create_using`` is a multigraph and the matrix has only integer entries
    but ``parallel_edges`` is ``True``, then the entries will be interpreted as
    the number of parallel edges joining those two vertices:

    >>> import numpy
    >>> A = numpy.matrix([[1, 1], [1, 2]])
    >>> temp = nx.MultiGraph()
    >>> G = nx.from_numpy_matrix(A, parallel_edges = True, create_using = temp)
    >>> G[1][1]
    {0: {'weight': 1}, 1: {'weight': 1}}

    User defined compound data type on edges:

    >>> import numpy
    >>> dt = [('weight', float), ('cost', int)]
    >>> A = numpy.matrix([[(1.0, 2)]], dtype = dt)
    >>> G = nx.from_numpy_matrix(A)
    >>> G.edges()
    [(0, 0)]
    >>> G[0][0]['cost']
    2
    >>> G[0][0]['weight']
    1.0

    """
    # This should never fail if you have created a numpy matrix with numpy...
    import numpy as np
    kind_to_python_type={'f':float,
                         'i':int,
                         'u':int,
                         'b':bool,
                         'c':complex,
                         'S':str,
                         'V':'void'}
    try: # Python 3.x
        blurb = chr(1245) # just to trigger the exception
        kind_to_python_type['U']=str
    except ValueError: # Python 2.6+
        kind_to_python_type['U']=unicode
    G=_prep_create_using(create_using)
    n,m=A.shape
    if n!=m:
        raise nx.NetworkXError("Adjacency matrix is not square.",
                               "nx,ny=%s"%(A.shape,))
    dt=A.dtype
    try:
        python_type=kind_to_python_type[dt.kind]
    except:
        raise TypeError("Unknown numpy data type: %s"%dt)

    # Make sure we get even the isolated nodes of the graph.
    G.add_nodes_from(range(n))
    # Get a list of all the entries in the matrix with nonzero entries. These
    # coordinates will become the edges in the graph.
    edges = zip(*(np.asarray(A).nonzero()))
    # handle numpy constructed data type
    if python_type == 'void':
        # Sort the fields by their offset, then by dtype, then by name.
        fields = sorted((offset, dtype, name) for name, (dtype, offset) in
                        A.dtype.fields.items())
        triples = ((u, v, {name: kind_to_python_type[dtype.kind](val)
                           for (_, dtype, name), val in zip(fields, A[u, v])})
                   for u, v in edges)
    # If the entries in the adjacency matrix are integers, the graph is a
    # multigraph, and parallel_edges is True, then create parallel edges, each
    # with weight 1, for each entry in the adjacency matrix. Otherwise, create
    # one edge for each positive entry in the adjacency matrix and set the
    # weight of that edge to be the entry in the matrix.
    elif python_type is int and G.is_multigraph() and parallel_edges:
        chain = itertools.chain.from_iterable
        # The following line is equivalent to:
        #
        #     for (u, v) in edges:
        #         for d in range(A[u, v]):
        #             G.add_edge(u, v, weight=1)
        #
        triples = chain(((u, v, dict(weight=1)) for d in range(A[u, v]))
                        for (u, v) in edges)
    else:  # basic data type
        triples = ((u, v, dict(weight=python_type(A[u, v])))
                   for u, v in edges)
    # If we are creating an undirected multigraph, only add the edges from the
    # upper triangle of the matrix. Otherwise, add all the edges. This relies
    # on the fact that the vertices created in the
    # ``_generated_weighted_edges()`` function are actually the row/column
    # indices for the matrix ``A``.
    #
    # Without this check, we run into a problem where each edge is added twice
    # when ``G.add_edges_from()`` is invoked below.
    if G.is_multigraph() and not G.is_directed():
        triples = ((u, v, d) for u, v, d in triples if u <= v)
    G.add_edges_from(triples)
    return G


@not_implemented_for('multigraph')
def to_numpy_recarray(G,nodelist=None,
                      dtype=[('weight',float)],
                      order=None):
    """Return the graph adjacency matrix as a NumPy recarray.

    Parameters
    ----------
    G : graph
        The NetworkX graph used to construct the NumPy matrix.

    nodelist : list, optional
       The rows and columns are ordered according to the nodes in `nodelist`.
       If `nodelist` is None, then the ordering is produced by G.nodes().

    dtype : NumPy data-type, optional
        A valid NumPy named dtype used to initialize the NumPy recarray.
        The data type names are assumed to be keys in the graph edge attribute
        dictionary.

    order : {'C', 'F'}, optional
        Whether to store multidimensional data in C- or Fortran-contiguous
        (row- or column-wise) order in memory. If None, then the NumPy default
        is used.

    Returns
    -------
    M : NumPy recarray
       The graph with specified edge data as a Numpy recarray

    Notes
    -----
    When `nodelist` does not contain every node in `G`, the matrix is built
    from the subgraph of `G` that is induced by the nodes in `nodelist`.

    Examples
    --------
    >>> G = nx.Graph()
    >>> G.add_edge(1,2,weight=7.0,cost=5)
    >>> A=nx.to_numpy_recarray(G,dtype=[('weight',float),('cost',int)])
    >>> print(A.weight)
    [[ 0.  7.]
     [ 7.  0.]]
    >>> print(A.cost)
    [[0 5]
     [5 0]]
    """
    import numpy as np
    if nodelist is None:
        nodelist = G.nodes()
    nodeset = set(nodelist)
    if len(nodelist) != len(nodeset):
        msg = "Ambiguous ordering: `nodelist` contained duplicates."
        raise nx.NetworkXError(msg)
    nlen=len(nodelist)
    undirected = not G.is_directed()
    index=dict(zip(nodelist,range(nlen)))
    M = np.zeros((nlen,nlen), dtype=dtype, order=order)

    names=M.dtype.names
    for u,v,attrs in G.edges_iter(data=True):
        if (u in nodeset) and (v in nodeset):
            i,j = index[u],index[v]
            values=tuple([attrs[n] for n in names])
            M[i,j] = values
            if undirected:
                M[j,i] = M[i,j]

    return M.view(np.recarray)


def to_scipy_sparse_matrix(G, nodelist=None, dtype=None,
                           weight='weight', format='csr'):
    """Return the graph adjacency matrix as a SciPy sparse matrix.

    Parameters
    ----------
    G : graph
        The NetworkX graph used to construct the NumPy matrix.

    nodelist : list, optional
       The rows and columns are ordered according to the nodes in `nodelist`.
       If `nodelist` is None, then the ordering is produced by G.nodes().

    dtype : NumPy data-type, optional
        A valid NumPy dtype used to initialize the array. If None, then the
        NumPy default is used.

    weight : string or None   optional (default='weight')
        The edge attribute that holds the numerical value used for
        the edge weight.  If None then all edge weights are 1.

    format : str in {'bsr', 'csr', 'csc', 'coo', 'lil', 'dia', 'dok'}
        The type of the matrix to be returned (default 'csr').  For
        some algorithms different implementations of sparse matrices
        can perform better.  See [1]_ for details.

    Returns
    -------
    M : SciPy sparse matrix
       Graph adjacency matrix.

    Notes
    -----
    The matrix entries are populated using the edge attribute held in
    parameter weight. When an edge does not have that attribute, the
    value of the entry is 1.

    For multiple edges the matrix values are the sums of the edge weights.

    When `nodelist` does not contain every node in `G`, the matrix is built
    from the subgraph of `G` that is induced by the nodes in `nodelist`.

    Uses coo_matrix format. To convert to other formats specify the
    format= keyword.

    The convention used for self-loop edges in graphs is to assign the
    diagonal matrix entry value to the weight attribute of the edge
    (or the number 1 if the edge has no weight attribute).  If the
    alternate convention of doubling the edge weight is desired the
    resulting Scipy sparse matrix can be modified as follows:

    >>> import scipy as sp
    >>> G = nx.Graph([(1,1)])
    >>> A = nx.to_scipy_sparse_matrix(G)
    >>> print(A.todense())
    [[1]]
    >>> A.setdiag(A.diagonal()*2)
    >>> print(A.todense())
    [[2]]

    Examples
    --------
    >>> G = nx.MultiDiGraph()
    >>> G.add_edge(0,1,weight=2)
    >>> G.add_edge(1,0)
    >>> G.add_edge(2,2,weight=3)
    >>> G.add_edge(2,2)
    >>> S = nx.to_scipy_sparse_matrix(G, nodelist=[0,1,2])
    >>> print(S.todense())
    [[0 2 0]
     [1 0 0]
     [0 0 4]]

    References
    ----------
    .. [1] Scipy Dev. References, "Sparse Matrices",
       http://docs.scipy.org/doc/scipy/reference/sparse.html
    """
    from scipy import sparse
    if nodelist is None:
        nodelist = G
    nlen = len(nodelist)
    if nlen == 0:
        raise nx.NetworkXError("Graph has no nodes or edges")

    if len(nodelist) != len(set(nodelist)):
        msg = "Ambiguous ordering: `nodelist` contained duplicates."
        raise nx.NetworkXError(msg)

    index = dict(zip(nodelist,range(nlen)))
    if G.number_of_edges() == 0:
        row,col,data=[],[],[]
    else:
        row,col,data = zip(*((index[u],index[v],d.get(weight,1))
                             for u,v,d in G.edges_iter(nodelist, data=True)
                             if u in index and v in index))
    if G.is_directed():
        M = sparse.coo_matrix((data,(row,col)),
                              shape=(nlen,nlen), dtype=dtype)
    else:
        # symmetrize matrix
        d = data + data
        r = row + col
        c = col + row
        # selfloop entries get double counted when symmetrizing
        # so we subtract the data on the diagonal
        selfloops = G.selfloop_edges(data=True)
        if selfloops:
            diag_index,diag_data = zip(*((index[u],-d.get(weight,1))
                                         for u,v,d in selfloops
                                         if u in index and v in index))
            d += diag_data
            r += diag_index
            c += diag_index
        M = sparse.coo_matrix((d, (r, c)), shape=(nlen,nlen), dtype=dtype)
    try:
        return M.asformat(format)
    except AttributeError:
        raise nx.NetworkXError("Unknown sparse matrix format: %s"%format)


def _csr_gen_triples(A):
    """Converts a SciPy sparse matrix in **Compressed Sparse Row** format to
    an iterable of weighted edge triples.

    """
    nrows = A.shape[0]
    data, indices, indptr = A.data, A.indices, A.indptr
    for i in range(nrows):
        for j in range(indptr[i], indptr[i+1]):
            yield i, indices[j], data[j]


def _csc_gen_triples(A):
    """Converts a SciPy sparse matrix in **Compressed Sparse Column** format to
    an iterable of weighted edge triples.

    """
    ncols = A.shape[1]
    data, indices, indptr = A.data, A.indices, A.indptr
    for i in range(ncols):
        for j in range(indptr[i], indptr[i+1]):
            yield indices[j], i, data[j]


def _coo_gen_triples(A):
    """Converts a SciPy sparse matrix in **Coordinate** format to an iterable
    of weighted edge triples.

    """
    row, col, data = A.row, A.col, A.data
    return zip(row, col, data)


def _dok_gen_triples(A):
    """Converts a SciPy sparse matrix in **Dictionary of Keys** format to an
    iterable of weighted edge triples.

    """
    for (r, c), v in A.items():
        yield r, c, v


def _generate_weighted_edges(A):
    """Returns an iterable over (u, v, w) triples, where u and v are adjacent
    vertices and w is the weight of the edge joining u and v.

    `A` is a SciPy sparse matrix (in any format).

    """
    if A.format == 'csr':
        return _csr_gen_triples(A)
    if A.format == 'csc':
        return _csc_gen_triples(A)
    if A.format == 'dok':
        return _dok_gen_triples(A)
    # If A is in any other format (including COO), convert it to COO format.
    return _coo_gen_triples(A.tocoo())


def from_scipy_sparse_matrix(A, parallel_edges=False, create_using=None,
                             edge_attribute='weight'):
    """Creates a new graph from an adjacency matrix given as a SciPy sparse
    matrix.

    Parameters
    ----------
    A: scipy sparse matrix
      An adjacency matrix representation of a graph

    parallel_edges : Boolean
      If this is ``True``, `create_using` is a multigraph, and `A` is an
      integer matrix, then entry *(i, j)* in the matrix is interpreted as the
      number of parallel edges joining vertices *i* and *j* in the graph. If it
      is ``False``, then the entries in the adjacency matrix are interpreted as
      the weight of a single edge joining the vertices.

    create_using: NetworkX graph
       Use specified graph for result.  The default is Graph()

    edge_attribute: string
       Name of edge attribute to store matrix numeric value. The data will
       have the same type as the matrix entry (int, float, (real,imag)).

    Notes
    -----

    If `create_using` is an instance of :class:`networkx.MultiGraph` or
    :class:`networkx.MultiDiGraph`, `parallel_edges` is ``True``, and the
    entries of `A` are of type ``int``, then this function returns a multigraph
    (of the same type as `create_using`) with parallel edges. In this case,
    `edge_attribute` will be ignored.

    If `create_using` is an undirected multigraph, then only the edges
    indicated by the upper triangle of the matrix `A` will be added to the
    graph.

    Examples
    --------
    >>> import scipy.sparse
    >>> A = scipy.sparse.eye(2,2,1)
    >>> G = nx.from_scipy_sparse_matrix(A)

    If `create_using` is a multigraph and the matrix has only integer entries,
    the entries will be interpreted as weighted edges joining the vertices
    (without creating parallel edges):

    >>> import scipy
    >>> A = scipy.sparse.csr_matrix([[1, 1], [1, 2]])
    >>> G = nx.from_scipy_sparse_matrix(A, create_using=nx.MultiGraph())
    >>> G[1][1]
    {0: {'weight': 2}}

    If `create_using` is a multigraph and the matrix has only integer entries
    but `parallel_edges` is ``True``, then the entries will be interpreted as
    the number of parallel edges joining those two vertices:

    >>> import scipy
    >>> A = scipy.sparse.csr_matrix([[1, 1], [1, 2]])
    >>> G = nx.from_scipy_sparse_matrix(A, parallel_edges=True,
    ...                                 create_using=nx.MultiGraph())
    >>> G[1][1]
    {0: {'weight': 1}, 1: {'weight': 1}}

    """
    G = _prep_create_using(create_using)
    n,m = A.shape
    if n != m:
        raise nx.NetworkXError(\
              "Adjacency matrix is not square. nx,ny=%s"%(A.shape,))
    # Make sure we get even the isolated nodes of the graph.
    G.add_nodes_from(range(n))
    # Create an iterable over (u, v, w) triples and for each triple, add an
    # edge from u to v with weight w.
    triples = _generate_weighted_edges(A)
    # If the entries in the adjacency matrix are integers, the graph is a
    # multigraph, and parallel_edges is True, then create parallel edges, each
    # with weight 1, for each entry in the adjacency matrix. Otherwise, create
    # one edge for each positive entry in the adjacency matrix and set the
    # weight of that edge to be the entry in the matrix.
    if A.dtype.kind in ('i', 'u') and G.is_multigraph() and parallel_edges:
        chain = itertools.chain.from_iterable
        # The following line is equivalent to:
        #
        #     for (u, v) in edges:
        #         for d in range(A[u, v]):
        #             G.add_edge(u, v, weight=1)
        #
        triples = chain(((u, v, 1) for d in range(w)) for (u, v, w) in triples)
    # If we are creating an undirected multigraph, only add the edges from the
    # upper triangle of the matrix. Otherwise, add all the edges. This relies
    # on the fact that the vertices created in the
    # ``_generated_weighted_edges()`` function are actually the row/column
    # indices for the matrix ``A``.
    #
    # Without this check, we run into a problem where each edge is added twice
    # when `G.add_weighted_edges_from()` is invoked below.
    if G.is_multigraph() and not G.is_directed():
        triples = ((u, v, d) for u, v, d in triples if u <= v)
    G.add_weighted_edges_from(triples, weight=edge_attribute)
    return G


# fixture for nose tests
def setup_module(module):
    from nose import SkipTest
    try:
        import numpy
    except:
        raise SkipTest("NumPy not available")
    try:
        import scipy
    except:
        raise SkipTest("SciPy not available")
    try:
        import pandas
    except:
        raise SkipTest("Pandas not available")
