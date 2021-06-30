import numpy as np
import tensorflow as tf
import tensorflow.keras as keras
import IPython

from tensorflow.keras.layers import Dense
# Import MNIST data
from tensorflow.keras.datasets import mnist

(x_train, y_train), (x_valid, y_valid) = mnist.load_data()

# Reduce size
train_size = 5000 # 60'000
valid_size = 750 # 10'000
x_train = x_train[:train_size]
x_valid = x_valid[:valid_size]
y_train = y_train[:train_size]
y_valid = y_valid[:valid_size]

x_train = x_train.reshape(train_size, 784)
x_valid = x_valid.reshape(valid_size, 784)
x_train = x_train / 255
x_valid = x_valid / 255

num_categories = 10
y_train = keras.utils.to_categorical(y_train, num_categories)
y_valid = keras.utils.to_categorical(y_valid, num_categories)

model = keras.models.Sequential()
model.add(Dense(units=512, activation='relu', input_shape=(784,)))
model.add(Dense(units = 512, activation='relu'))
model.add(Dense(units = 10, activation='softmax'))

print(model.summary())

model.compile(loss='categorical_crossentropy', metrics=['accuracy'])
history = model.fit(
    x_train, y_train, epochs=5, verbose=1, validation_data=(x_valid, y_valid)
)

# Cleaning the kernel
# app = IPython.Application.instance()
# app.kernel.do_shutdown(True)