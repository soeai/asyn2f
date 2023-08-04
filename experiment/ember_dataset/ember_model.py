
import tensorflow as tf

from asynfed.client.frameworks.tensorflow import TensorflowSequentialModel
from asynfed.client.config_structure import LearningRateConfig


class EmberModel(TensorflowSequentialModel):
    def __init__(self, input_features = (2**10), output_features = 1, lr_config: dict = None):
        lr_config = lr_config or {}
        self.lr_config = LearningRateConfig(**lr_config)
        print("Config in the resnet model")
        print(self.lr_config.to_dict())
        super().__init__(input_features=input_features, output_features=output_features)

        print(f"Learning rate right now is: {self.get_learning_rate()}")

    def get_optimizer(self):
        return self.optimizer

    def set_learning_rate(self, lr):
        return self.optimizer.lr.assign(lr)

    def get_learning_rate(self):
        return self.optimizer.lr.numpy()

    def create_model(self, input_features, output_features):
        input_dim= 257
        maxlen= 2**20
        embedding_size=8

        # self.input_dim = input_dim
        # self.maxlen = maxlen
        # self.embedding_size = embedding_size

        inp = tf.keras.layers.Input(shape=(maxlen,))
        emb = tf.keras.layers.Embedding(input_dim, embedding_size)(inp)
        filt = tf.keras.layers.Conv1D(filters=128, kernel_size=500, strides=500, use_bias=True, activation='relu', padding='valid')(emb)
        attn = tf.keras.layers.Conv1D(filters=128, kernel_size=500, strides=500, use_bias=True, activation='sigmoid', padding='valid')(emb)
        gated = tf.keras.layers.Multiply()([filt, attn])
        feat = tf.keras.layers.GlobalMaxPooling1D()(gated)
        dense = tf.keras.layers.Dense(128, activation='relu')(feat)
        outp = tf.keras.layers.Dense(1, activation='sigmoid')(dense)

        self.model = tf.keras.models.Model(inp, outp)
        self.model.summary()

    def call(self, x):
        return self.model(x)

    def create_loss_object(self):
        return tf.keras.losses.BinaryCrossentropy()

    def create_optimizer(self):
        if self.lr_config.fix_lr:
            optimizer = tf.keras.optimizers.SGD(learning_rate= self.lr_config.lr, momentum= 0.9)
            print(f"Create optimizer with fix learning rate: {optimizer.lr.numpy()}")
        else:
            lr_scheduler = tf.keras.experimental.CosineDecay(initial_learning_rate= self.lr_config.lr,
                                                         decay_steps= self.lr_config.decay_steps)
            optimizer = tf.keras.optimizers.SGD(learning_rate=lr_scheduler, momentum=0.9)
            print(f"Create optimizer with decay learning rate: {optimizer.lr.numpy()}")

        return optimizer

    def create_train_metric(self):
        return tf.keras.metrics.BinaryAccuracy(name='train_accuracy'), tf.keras.metrics.Mean(name='train_loss')

    def create_test_metric(self):
        return tf.keras.metrics.BinaryAccuracy(name='test_accuracy'), tf.keras.metrics.Mean(name='test_loss')

    def get_train_performance(self):
        return float(self.train_performance.result())

    def get_train_loss(self):
        return float(self.train_loss.result())

    def get_test_performance(self):
        return float(self.test_performance.result())

    def get_test_loss(self):
        return float(self.test_loss.result())


