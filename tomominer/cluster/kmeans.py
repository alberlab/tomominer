
# non-parallel k-means.
def kmeans_clustering(data, k):
  """
  TODO: add docs

  :param data:
    :param k:
  """

  from scipy.cluster.vq import kmeans, vq, whiten

  data = whiten(data)
  centroids, _ = kmeans(data, k)
  labels,  _ = vq(data, centroids)

  return labels

