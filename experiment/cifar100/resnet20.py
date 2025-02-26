import tensorflow as tf
import numpy as np

from asynfed.client.frameworks.tensorflow import TensorflowSequentialModel
from asynfed.client.config_structure import LearningRateConfig


class CustomCosineDecay(tf.keras.optimizers.schedules.LearningRateSchedule):
    def __init__(self, initial_learning_rate, decay_steps, min_learning_rate=0.001):
        self.initial_learning_rate = initial_learning_rate
        self.decay_steps = decay_steps
        self.min_learning_rate = min_learning_rate

    def __call__(self, step):
        
        def true_fn():
            return self.min_learning_rate
        
        def false_fn():
            cosine_decay = 0.5 * (1 + tf.math.cos(tf.constant(np.pi) * tf.cast(step, tf.float32) / tf.cast(self.decay_steps, tf.float32)))
            decayed = (1 - self.min_learning_rate) * cosine_decay + self.min_learning_rate
            return self.initial_learning_rate * decayed
        
        condition = tf.greater_equal(step, self.decay_steps)
        return tf.cond(condition, true_fn, false_fn)

    def get_config(self):
        return {
            "initial_learning_rate": self.initial_learning_rate,
            "decay_steps": self.decay_steps,
            "min_learning_rate": self.min_learning_rate,
        }


class ResNetLayer(tf.keras.Model):
    def __init__(self, num_filters=16, kernel_size=3, strides=1, activation='relu', batch_normalization=True):
        super(ResNetLayer, self).__init__()
        self.conv = tf.keras.layers.Conv2D(num_filters, kernel_size=kernel_size, strides=strides, padding='same')
        self.batch_norm = tf.keras.layers.BatchNormalization() if batch_normalization else None
        self.activation = tf.keras.layers.Activation(activation) if activation is not None else None

    def call(self, x):
        x = self.conv(x)
        if self.batch_norm:
            x = self.batch_norm(x)
        if self.activation:
            x = self.activation(x)
        return x


class BasicBlock(tf.keras.Model):
    expansion = 1

    def __init__(self, in_channels, out_channels, strides=1):
        super(BasicBlock, self).__init__()
        
        self.conv1 = ResNetLayer(num_filters=out_channels, kernel_size=3, strides=strides)
        self.conv2 = ResNetLayer(num_filters=out_channels, kernel_size=3, strides=1, activation=None)
        
        if strides != 1 or in_channels != self.expansion * out_channels:
            self.shortcut = tf.keras.Sequential([
                tf.keras.layers.Conv2D(self.expansion * out_channels, kernel_size=1, strides=strides, use_bias=False),
                tf.keras.layers.BatchNormalization()
            ])
        else:
            self.shortcut = lambda x: x
            # self.shortcut = lambda x, training: x

    def call(self, x):
        out = self.conv1(x)
        out = self.conv2(out)
        out += self.shortcut(x)
        return tf.keras.activations.relu(out)


class Resnet20(TensorflowSequentialModel):
    def __init__(self, input_features = (32, 32, 3), output_features = 100, lr_config: dict = None, 
                 depth=20):
        lr_config = lr_config or {}
        self.lr_config = LearningRateConfig(**lr_config)
        self.depth = depth
        print("lr config in the resnet model")
        print(self.lr_config.to_dict())
        super().__init__(input_features=input_features, output_features=output_features)

        print(f"Learning rate right now (step = 0) is: {self.get_learning_rate()}")


    def get_optimizer(self):
        return self.optimizer
    
    
    def set_learning_rate(self, lr):
        return self.optimizer.learning_rate.assign(lr)

    def get_learning_rate(self):
        return self.optimizer.learning_rate.numpy()


    def create_model(self, input_features, output_features):
        num_filters = 16
        num_res_blocks = (self.depth - 2) // 6
        self.in_channels = num_filters

        self.conv1 = ResNetLayer(num_filters=num_filters, kernel_size=3, strides=1)

        self.stack1 = self._make_layer(BasicBlock, num_filters, num_res_blocks, strides=1)
        self.stack2 = self._make_layer(BasicBlock, num_filters * 2, num_res_blocks, strides=2)
        self.stack3 = self._make_layer(BasicBlock, num_filters * 4, num_res_blocks, strides=2)

        self.avg_pool = tf.keras.layers.AveragePooling2D(pool_size=8)
        self.flatten = tf.keras.layers.Flatten()
        self.fc = tf.keras.layers.Dense(output_features, activation='softmax')

    def create_loss_object(self):
        return tf.keras.losses.CategoricalCrossentropy()

    def create_optimizer(self):
        if self.lr_config.fix_lr:
            optimizer = tf.keras.optimizers.SGD(learning_rate= self.lr_config.initial_lr, momentum= 0.9)
            print(f"Create optimizer with fix learning rate: {optimizer.learning_rate.numpy()}")

        else:
            lr_scheduler = CustomCosineDecay(initial_learning_rate= self.lr_config.initial_lr, 
                                            decay_steps= self.lr_config.decay_steps,
                                            min_learning_rate= self.lr_config.min_lr)

            optimizer = tf.keras.optimizers.SGD(learning_rate=lr_scheduler, momentum=0.9)
            print(f"Create optimizer using lr with decay step. This is the initial learning rate: {optimizer.learning_rate.numpy()}")
            print(f"This is the lr of the lr schedule when current step = decay steps: {float(lr_scheduler(self.lr_config.decay_steps))}")
            print(f"This is the min lr of the lr scheduler: {float(lr_scheduler(self.lr_config.decay_steps + 1))}")

        return optimizer


    def create_train_metric(self):
        return tf.keras.metrics.CategoricalAccuracy(name='train_accuracy'), tf.keras.metrics.Mean(
            name='train_loss')

    def create_test_metric(self):
        return tf.keras.metrics.CategoricalAccuracy(name='test_accuracy'), tf.keras.metrics.Mean(name='test_loss')

    def get_train_performance(self):
        return float(self.train_performance.result())

    def get_test_performance(self):
        return float(self.test_performance.result())

    def get_train_loss(self):
        return float(self.train_loss.result())

    def get_test_loss(self):
        return float(self.test_loss.result())

    def _make_layer(self, block, out_channels, num_blocks, strides):
        strides_list = [strides] + [1] * (num_blocks - 1)
        layers = []
        for s in strides_list:
            layers.append(block(self.in_channels, out_channels, s))
            self.in_channels = out_channels * block.expansion
        return tf.keras.Sequential(layers)

    def call(self, x):
        x = self.conv1(x)
        x = self.stack1(x)
        x = self.stack2(x)
        x = self.stack3(x)
        x = self.avg_pool(x)
        x = self.flatten(x)
        x = self.fc(x)
        return x