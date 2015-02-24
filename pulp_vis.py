from sys import exit, stderr, argv
import numpy
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import scipy.sparse
import json
from sklearn import manifold, random_projection

# http://scikit-learn.org/stable/auto_examples/manifold/plot_compare_methods.html
# http://scikit-learn.org/stable/modules/manifold.html

def save_sparse(m, prefix) :
    numpy.save(prefix + '.data.npy',     m.data)
    numpy.save(prefix + '.indices.npy',  m.indices)
    numpy.save(prefix + '.indptr.npy',   m.indptr)
    numpy.save(prefix + '.shape.npy',    m.shape)

def load_data_sparse(prefix) :
    return scipy.sparse.csr_matrix((numpy.load(prefix + '.data.npy'),
                                    numpy.load(prefix + '.indices.npy'),
                                    numpy.load(prefix + '.indptr.npy')),
                                    shape=tuple(numpy.load(prefix + '.shape.npy')))

def load_data() :
    return load_data_sparse('linrel')

def load_json(fname) :
    with open(fname) as f :
        return json.load(f)

def load_features() :
    return load_json('linrel_features.json')

def load_topics() :
    return load_json('linrel_topics.json')

def main() :

    method = argv[1]

    if method not in ('ltsa','mds','isomap','spectral','tsne') :
        print >> stderr, "FUCK YOU TALKIN' 'ABOUT?"
        exit(1)

    # load + constants
    print >> stderr, "loading data..."
    data = load_data()
    num_articles, num_features = data.shape
    num_neighbours = 10
    id2topic = load_topics()
    
    for k in id2topic :
        v = id2topic[k]
        if "." in v :
            id2topic[k] = v.split(".")[0]

    num_components = len(set(id2topic.values()))
    colours = [ id2topic[str(k)] for k in sorted([ int(i) for i in id2topic.keys() ]) ]
    print >> stderr, "loaded %d articles x %d features" % (num_articles, num_features)
    print >> stderr, "  ... with %d components" % num_components

    print >> stderr, colours[:10]

    # transform
    print >> stderr, "transforming..."
    if method == 'ltsa' :
        t = manifold.LocallyLinearEmbedding(num_neighbours, 
                                            num_components,
                                            eigen_solver='auto',
                                            method='ltsa')

    elif method == 'mds' :
        t = manifold.MDS(num_components, 
                         max_iter=100, 
                         n_init=1)

    elif method == 'isomap' :
        t = manifold.Isomap(num_neighbours, 
                            num_components)

    elif method == 'spectral' :
        t = manifold.SpectralEmbedding(n_components=num_components,
                                       n_neighbors=num_neighbours)

    elif method == 'tsne' :
        t = manifold.TSNE(n_components=num_components, 
                          init='pca', 
                          random_state=0)

    t.fit_transform(data.toarray())

    save_data(X, method)
    return 0


#    X = random_projection.SparseRandomProjection(n_components=2, random_state=42).fit_transform(data)
    print >> stderr, "transform done, shape =", X.shape

    # normalise
    #x_min, x_max = numpy.min(X, 0), numpy.max(X, 0)
    #X = (X - x_min) / (x_max - x_min)

    X = X.toarray()

#    print >> stderr, colours.shape

#    print >> stderr, X.shape
#    print >> stderr, X[:,0].shape
#    print >> stderr, X[:,1].shape

    df = pd.DataFrame(dict(x=X[:,0], y=X[:,1], colours=colours))

    sns.lmplot('x', 'y', data=df, hue='colours', fit_reg=False)

    # plot
#    plt.scatter(X[:, 0], 
#                X[:, 1],
#                c=colours, 
#                cmap=plt.cm.Spectral)
    
#    plt.legend()
    plt.show()

if __name__ == '__main__' :
    try :
        exit(main())
    except KeyboardInterrupt :
        print >> stderr, "Killed by User...\n"
        exit(1)

