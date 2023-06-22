'''
ResNet18/34/50/101/152 in TensorFlow2.

Reference:
[1] He, Kaiming, et al.
    "Deep residual learning for image recognition."
    Proceedings of the IEEE conference on computer vision and pattern recognition. 2016.
'''
import tensorflow as tf
from tensorflow.keras import layers
from asynfed.client import TensorflowSequentialModel


class BasicBlock(tf.keras.Model):
    expansion = 1

    def __init__(self, in_channels, out_channels, strides=1):
        super(BasicBlock, self).__init__()
        self.conv1 = layers.Conv2D(out_channels, kernel_size=3, strides=strides, padding='same', use_bias=False)
        self.bn1 = layers.BatchNormalization()
        self.conv2 = layers.Conv2D(out_channels, kernel_size=3, strides=1, padding='same', use_bias=False)
        self.bn2 = layers.BatchNormalization()

        if strides != 1 or in_channels != self.expansion * out_channels:
            self.shortcut = tf.keras.Sequential([
                layers.Conv2D(self.expansion * out_channels, kernel_size=1, strides=strides, use_bias=False),
                layers.BatchNormalization()
            ])
        else:
            self.shortcut = lambda x: x

    def call(self, x):
        out = tf.keras.activations.relu(self.bn1(self.conv1(x)))
        out = self.bn2(self.conv2(out))
        out = layers.add([self.shortcut(x), out])
        out = tf.keras.activations.relu(out)
        return out



class Resnet18(TensorflowSequentialModel):
    def __init__(self, input_features, output_features, lr, decay_steps):
        super().__init__(input_features=input_features, output_features=output_features,
                         learning_rate_fn=tf.keras.experimental.CosineDecay(lr, decay_steps=decay_steps))

    def create_model(self, input_features, output_features):
        self.in_channels = 64
        num_blocks = [2, 2, 2, 2]

        self.conv1 = layers.Conv2D(64, kernel_size=3, strides=1, padding='same', use_bias=False, input_shape= input_features)
        self.bn1 = layers.BatchNormalization()
        self.layer1 = self._make_layer(BasicBlock, 64, num_blocks[0], strides=1)
        self.layer2 = self._make_layer(BasicBlock, 128, num_blocks[1], strides=2)
        self.layer3 = self._make_layer(BasicBlock, 256, num_blocks[2], strides=2)
        self.layer4 = self._make_layer(BasicBlock, 512, num_blocks[3], strides=2)
        self.avg_pool2d = layers.AveragePooling2D(pool_size=4)
        self.flatten = layers.Flatten()
        self.fc = layers.Dense(output_features, activation='softmax')

    def call(self, x):
        out = tf.keras.activations.relu(self.bn1(self.conv1(x)))
        out = self.layer1(out)
        out = self.layer2(out)
        out = self.layer3(out)
        out = self.layer4(out)
        out = self.avg_pool2d(out)
        out = self.flatten(out)
        out = self.fc(out)
        return out

    def create_loss_object(self):
        return tf.keras.losses.CategoricalCrossentropy()

    def create_optimizer(self, learning_rate_fn):
        return tf.keras.optimizers.SGD(learning_rate=learning_rate_fn, momentum=0.9)

    def create_train_metric(self):
        return tf.keras.metrics.CategoricalAccuracy(name='train_accuracy'), tf.keras.metrics.Mean(
            name='train_loss')

    def create_test_metric(self):
        return tf.keras.metrics.CategoricalAccuracy(name='test_accuracy'), tf.keras.metrics.Mean(name='test_loss')

    def get_train_performance(self):
        return float(self.train_performance.result())

    def get_train_loss(self):
        return float(self.train_loss.result())

    def get_test_performance(self):
        return float(self.test_performance.result())

    def get_test_loss(self):
        return float(self.test_loss.result())

    def _make_layer(self, block, out_channels, num_blocks, strides):
        stride = [strides] + [1] * (num_blocks - 1)
        layer = []
        for s in stride:
            layer += [block(self.in_channels, out_channels, s)]
            self.in_channels = out_channels * block.expansion
        return tf.keras.Sequential(layer)


