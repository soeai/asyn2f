import tensorflow as tf
# from tensorflow.keras import Model, Input
from resnet20 import get_network

# model = tf.keras.applications.ResNet50(
#     include_top=True,
#     weights=None,
#     input_shape=(32, 32, 3),
#     classes=100,
#     classifier_activation='softmax'
# )

model = get_network(return_before_head=False)
(x_train, y_train), (x_test, y_test) = tf.keras.datasets.cifar100.load_data()

model.compile(optimizer="adam", loss="sparse_categorical_crossentropy", metrics=['accuracy'])
model.fit(x_train, y_train, batch_size=128,epochs=100,validation_data=(x_test, y_test))