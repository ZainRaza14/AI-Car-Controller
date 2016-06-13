import numpy as np
import pdb

def affine_forward(x, w, b):
  out = None
  out = np.dot(x,w)
  out += b
  cache = (x, w, b)
  return out, cache


def affine_backward(dout, cache):
  
  x, w, b = cache
  dx, dw, db = None, None, None
  
  dw = np.dot(x.T, dout)
  dx = np.dot(dout, w.T)
  db = np.sum(dout, axis=0)

  return dx, dw, db


def relu_forward(x):
  
  out = None
  out = np.maximum(0, x)

  cache = x
  return out, cache


def relu_backward(dout, cache):

  dx, x = None, cache
  dx = dout * (np.maximum(0, x) / x)
  return dx


def softmax_loss(x, y):

  probs = np.exp(x - np.max(x, axis=1, keepdims=True))
  probs /= np.sum(probs, axis=1, keepdims=True)
  N = x.shape[0]
  loss = -np.sum(np.log(probs[np.arange(N), y])) / N
  dx = probs.copy()
  dx[np.arange(N), y] -= 1
  dx /= N
  return loss, dx
