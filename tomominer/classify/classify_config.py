
import os, json
import numpy as np

# TODO: Not all options set are parsed: e.g. cluster_min_size
# And some are parsed but not preset: template_cluster_size_min

class config_options:
  """
  This class holds all of the configuration parameters for a classification
  simulation.  The components are all set to default values where possible in
  __init__.  The function parse_config() is used to parse a json formatted
  file which overwrites these defaults.
  """

  def __init__(self):
    # set some defaults.
    self.root = "./"
    """The location of the simulation root."""

    self.iterations = 10
    """Number of iterations to run"""

    self.log_level = 0
    """Currently unused.  In the future will influence how much information
    is presented to the user"""

    # Clustering/Dimension reduction parameters.

    self.cluster_dimension_reduction_dims       = 100
    """Number of dimensions we will reduce to in the dimension reduction
    code."""

    self.cluster_dimension_reduction_max_features   = 1000
    """Number of input dimensions to use in dimension reduction"""

    self.cluster_dimension_reduction_iterations   = 15
    """Number of iterations of dimension reduction to carry out, if a
    parameter."""

    self.cluster_dimension_reduction_use_fft_avg    = True
    """Determines if we use the FFT-space averaging.  If false a simple
    average of the volumes ignoring the masks is used."""

    self.cluster_dimension_reduction_gauss_smoothing_sigma = 0.0

    self.cluster_use_fft_avg    = True
    """Use fft averaging when computing cluster centers"""

    self.cluster_min_size       = 0
    """Filter out clusters smaller then this size"""

    self.do_clustering        = False
    """Set to true if we will do clustering.  If false, all subtomograms
    will be averaged together"""

    self.cluster_method       = None
    """Cluster method to use: kmeans or hierarchical"""

    self.cluster_kmeans_k       = 0
    """If kmeans is the clustering method, This is the k value used."""

    self.cluster_kmeans_iterations  = 10
    """Number of k-means iterations."""

    self.template_align_corr_threshold = 1.0
    """Filter out templates that are more similar then this to the largest
    cluster center."""

    self.given_templates = []
    """A list of templates that will be used in addition to those found by
    clustering"""

    self.L = 36
    """Angle resolution parameter"""


  def parse_config(self, opt_file):
    """
    Parse a configuration file.  This will overwrite the default options
    set in the __init__ of the class definition.

    :param opt_file: A JSON formatted file with a dictionary hierarchy for options of differnt software components.
    """

    f = open(opt_file)
    conf = json.load(f)
    f.close()

    if 'iterations'  in conf: self.iterations = int(conf['iterations'])
    if 'log_level'   in conf: self.log_level  = int(conf['log_level'])

    if 'cluster' in conf:
      self.do_clustering = True
      cluster = conf['cluster']

      if 'min_size' in cluster:
        self.cluster_min_size = cluster['min_size']

      if 'dimension_reduction' in cluster:
        dim_red = cluster['dimension_reduction']
        if 'dims' in dim_red:
          self.cluster_dimension_reduction_dims = dim_red['dims']
        if 'max_features' in dim_red:
          self.cluster_dimension_reduction_max_features = dim_red['max_features']
        if 'iterations' in dim_red:
          self.cluster_dimension_reduction_iterations = dim_red['iterations']
        if 'use_fft_avg' in dim_red:
          self.cluster_dimension_reduction_use_fft_avg = dim_red['use_fft_avg']

      if 'kmeans' in cluster:
        self.cluster_method = 'kmeans'

        kmeans = cluster['kmeans']

        if 'k' in kmeans:
          self.cluster_kmeans_k = kmeans['k']
        if 'iterations' in kmeans:
          self.cluster_kmeans_iterations = kmeans['iterations']

      elif 'hierarchical' in cluster:
        self.cluster_method = 'hierarchical'

        # sel.cluster_hierarchical_threshold
      else:
        print cluster
        raise Exception("No clustering or unrecognized clustering method!")

    if 'template' in conf:
      template = conf['template']
      if 'align_corr_threshold'  in template:
        self.template_align_corr_threshold = float(template['align_corr_threshold'])
      if 'given_templates' in template:
        for i in range(len(template['given_templates'])):
          self.given_templates.append(  ( str(template['given_templates'][i][0]),  str(template['given_templates'][i][1]) )  )

    if 'L' in conf: self.L = int(conf['L'])


def parse_data(conf):
  """
  Parse data on subtomogram locations, and transformations.

  :param conf: A configuration string in JSON format.

  The JSON object is assumed to be a list of dictionaries.  Each dictionary
  is checked for four keys.  subtomogram, mask, angle, and loc.  The
  subtomogram is the only required field.  It must give a disk location for
  loading the subtomogram.  The mask is also a file location but is optional.
  The angle and loc are both arrays of length 3.  The angle is parsed as a
  ZYZ Euler angle.  The loc is the displacement shift for alignment.

  Any missing data is filled in, and a list data structure, with a list of
  tuples for each record is returned.
  """

  subs = []
  for record in conf:
    if 'subtomogram' not in record:
      raise Exception(repr(record))
    vol_path = record['subtomogram']

    # convert to absolute path if needed
    if not os.path.isabs(vol_path):
        vol_path = os.path.abspath(vol_path)
    assert os.path.isfile(vol_path)     # make sure that the file exists

    if 'mask' not in record:
      raise Exception(repr(record))
    mask_path = record['mask']

    # convert to absolute path if needed
    if not os.path.isabs(mask_path):
        mask_path = os.path.abspath(mask_path)
    assert os.path.isfile(mask_path)     # make sure that the file exists


    if 'angle' in record:
      if len(record['angle']) != 3:
        raise
      ang = np.array([float(_) for _ in record['angle']])
    else:
      ang = np.zeros(3, dtype=np.float)

    if "loc" in record:
      if len(record["loc"]) != 3:
        raise
      loc = np.array([float(_) for _ in record["loc"]])
    else:
      loc = np.zeros(3, dtype=np.float)
    subs.append((str(vol_path), str(mask_path), ang, loc))
  return subs
