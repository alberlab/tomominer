
from scipy.cluster.hierarchy import linkage, fcluster
from scipy.spatial.distance  import pdist, squareform

from sklearn.metrics     import silhouette_score

inf = float('inf')

def hierarchical_clustering(data):
  """
  Perform hierarchical clustering on the observation matrix.

  First we convert the observations to a distance matrix.  From the distance
  matrix, we compute the entire hierarchical clustering tree, and then walk
  the levels to find the best cutoff according to the silhouette score
  metric.

  :param data: The observation matrix.
  :returns: The labels of the best clustering found.
  """

  # convert observations to distances, using euclidean metric.
  # dist will be a compressed distance matrix.
  dist  = pdist(data)
  # Convert the distance matrix to a square matrix.
  dist_sq = squareform(dist)

  # hierarchical clustering from scipy.cluster
  link = linkage(dist)

  # calculate silhouette for each level.  
  # Find the optimal level according to silhouette_score.

  best_score = -inf
  best_label = None

  for i in range(link.shape[0]-1):
    # threshold = link[:,2]
    label  = fcluster(link, link[i,2], criterion='distance')
    score  = silhouette_score(dist_sq, label, metric='precomputed')

    if score > best_score:
      best_score  = score
      best_label  = label

  # return the best labels we have found.
  return best_label, dist_sq
