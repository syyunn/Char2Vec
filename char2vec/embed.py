
import numpy as np
import tensorflow as tf
from .utils import Tokenizer, ALPHABET, normalized, next_line_with_rotation
from collections import deque
from functools import partial

class CONFIG:
  """Model hyperparams"""
  D = 10          # embedding dimension
  WINDOW_SIZES = [1,2]
  BATCH = 32
  SHUFF_BUFFER = 10000
  TOTAL_STEPS = 20000
  GPU = False

class Char2Vec(object):

  def __init__(self, config=CONFIG, alphabet=ALPHABET, unk='~', DTYPE=tf.float32):
    self.cfg = config
    self.graph = tf.Graph()
    self.DTYPE = DTYPE
    self.tokenizer = Tokenizer(alphabet, unk)
    self.V = self.tokenizer.V
    self.N_HEADS = 2 * len(config.WINDOW_SIZES)

  def create_graph(self, corpus_path):
    with self.graph.as_default():
      dataset = tf.data.Dataset().from_generator(
        self.data_generator,
        (self.DTYPE, self.DTYPE),
        (tf.TensorShape([self.V]), tf.TensorShape([self.N_HEADS*self.V])),
        args=[corpus_path, self.cfg.WINDOW_SIZES]
      )
      dataset = dataset.shuffle(self.cfg.SHUFF_BUFFER)
      self.dataset = dataset.batch(self.cfg.BATCH)
      self.data_iter = self.dataset.make_initializable_iterator()
      self.x_in, self.y_labels = self.data_iter.get_next()

      device = '/device:GPU:0' if self.cfg.GPU else '/cpu:0'
      with self.graph.device(device):
        self.U = tf.get_variable(dtype=self.DTYPE, shape=[self.V, self.cfg.D], name='U')
        self.rep = tf.matmul(self.x_in, self.U)   # shape [batch_size, D]
        self.W = tf.get_variable(dtype=self.DTYPE,
                               shape=[self.cfg.D, self.N_HEADS*self.V],
                               name='W')
        self.logits = tf.matmul(self.rep, self.W)  # shape [batch_size, N*V]

        self.loss = tf.reduce_mean(tf.nn.sigmoid_cross_entropy_with_logits(
          labels=self.y_labels, logits=self.logits
        ))
        self._optimizer = tf.train.AdamOptimizer()
        self.train_step = self._optimizer.minimize(self.loss)
      self.__graph_created = True

  def data_generator(self, corpus_path, window_sizes):
    max_window = max(window_sizes)
    length = 1 + 2*max_window
    with open(corpus_path, 'r', encoding='utf-8') as f:
      pos = 0
      buffer = deque([])
      while True:
        # extend buffer to be enough
        while len(buffer) < length*10:
          buffer.extend(next_line_with_rotation(f).lower())

        window = [buffer[i] for i in range(length)]
        buffer.popleft()
        #yield self._xy_arrays(window, midpos=max_window)
        yield self._xy_arrays_sigmoid(window, midpos=max_window)

  def _xy_arrays(self, window, midpos):
    X = self.tokenizer.to_1hot(window[midpos]).flatten()  #length V
    Ys = []
    for s in self.cfg.WINDOW_SIZES:
      t_left = [window[midpos - 1 - i] for i in range(s)]
      t_right = [window[midpos + 1 + i] for i in range(s)]
      Ys.append(normalized(self.tokenizer.to_1hot(t_left).sum(axis=0)))
      Ys.append(normalized(self.tokenizer.to_1hot(t_right).sum(axis=0)))
    Y = normalized(np.concatenate(Ys))
    return X, Y

  def _xy_arrays_sigmoid(self, window, midpos):
    X = self.tokenizer.to_1hot(window[midpos]).flatten()  #length V
    Ys = []
    for s in self.cfg.WINDOW_SIZES:
      t_left = [window[midpos - 1 - i] for i in range(s)]
      t_right = [window[midpos + 1 + i] for i in range(s)]
      Ys.append(self.tokenizer.to_1hot(t_left).sum(axis=0))
      Ys.append(self.tokenizer.to_1hot(t_right).sum(axis=0))
    Y = np.concatenate(Ys)
    Y = (Y > 0).astype(np.float32)
    return X, Y

  def fit(self, path_to_corpus):
    pass #TODO


class CharGloVe(object):
  # TODO
  pass
