import tensorflow as tf
from asynfed.client.frameworks.tensorflow import TensorflowSequentialModel
from asynfed.client.config_structure import LearningRateConfig
import numpy as np

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


class F1Score(tf.keras.metrics.Metric):
    def __init__(self, name="f1_score", **kwargs):
        super(F1Score, self).__init__(name=name, **kwargs)
        self.precision = tf.keras.metrics.Precision()
        self.recall = tf.keras.metrics.Recall()

    def update_state(self, y_true, y_pred, sample_weight=None):
        self.precision.update_state(y_true, y_pred, sample_weight)
        self.recall.update_state(y_true, y_pred, sample_weight)

    def result(self):
        precision = self.precision.result()
        recall = self.recall.result()
        return 2 * ((precision * recall) / (precision + recall + 1e-6))

    def reset_states(self):
        self.precision.reset_states()
        self.recall.reset_states()


class WeightedBinaryCrossentropy(tf.keras.losses.Loss):
    def __init__(self, class_weight, **kwargs):
        super(WeightedBinaryCrossentropy, self).__init__(**kwargs)
        self.class_weight = tf.convert_to_tensor(class_weight, dtype=tf.float32)

    def call(self, y_true, y_pred):
        y_true = tf.reshape(y_true, [-1, 1])  # Reshape y_true to align with y_pred
        weights = tf.gather(self.class_weight, tf.cast(y_true, tf.int32))
        entropy = tf.keras.losses.binary_crossentropy(y_true, y_pred)
        return tf.reduce_mean(entropy * weights)



class EmberModel(TensorflowSequentialModel):
    def __init__(self, input_features = 2381, output_features = 1, input_dim: int = 261,
                    lr_config: dict = None, class_weight: dict= None):
        lr_config = lr_config or {}
        self.lr_config = LearningRateConfig(**lr_config)
        print("lr config in the resnet model")
        print(self.lr_config.to_dict())
        if class_weight:
          self.class_weight = class_weight
        else:
          self.class_weight = None
        
        self.input_dim = input_dim

        super().__init__(input_features=input_features, output_features=output_features)

        print(f"Learning rate right now (step = 0) is: {self.get_learning_rate()}")


    def get_optimizer(self):
        return self.optimizer

    def set_learning_rate(self, lr):
        return self.optimizer.lr.assign(lr)

    def get_learning_rate(self):
        return self.optimizer.lr.numpy()

    def create_model(self, input_features, output_features):
        # input_dim= 257
        input_dim = self.input_dim or 261
        embedding_size=8

        inp = tf.keras.layers.Input(shape=(input_features,))
        emb = tf.keras.layers.Embedding(input_dim, embedding_size)(inp)
        
        filt = tf.keras.layers.Conv1D(filters=128, kernel_size=15, strides=15, use_bias=True, activation='relu', padding='valid')(emb)
        attn = tf.keras.layers.Conv1D(filters=128, kernel_size=15, strides=15, use_bias=True, activation='sigmoid', padding='valid')(emb)
        
        gated = tf.keras.layers.Multiply()([filt, attn])
        feat = tf.keras.layers.GlobalMaxPooling1D()(gated)
        dense = tf.keras.layers.Dense(128, activation='relu')(feat)
        outp = tf.keras.layers.Dense(1, activation='sigmoid')(dense)

        self.model = tf.keras.models.Model(inp, outp)
        self.model.summary()

    def call(self, x):
        return self.model(x)

    def create_loss_object(self):
        if self.class_weight:
          return WeightedBinaryCrossentropy(class_weight= self.class_weight)
        return tf.keras.losses.BinaryCrossentropy()

    def create_optimizer(self):
        if self.lr_config.fix_lr:
            optimizer = tf.keras.optimizers.SGD(learning_rate= self.lr_config.initial_lr, momentum= 0.9)
            print(f"Create optimizer with fix learning rate: {optimizer.lr.numpy()}")

        else:
            lr_scheduler = CustomCosineDecay(initial_learning_rate= self.lr_config.initial_lr,
                                            decay_steps= self.lr_config.decay_steps,
                                            min_learning_rate= self.lr_config.min_lr)

            optimizer = tf.keras.optimizers.SGD(learning_rate=lr_scheduler, momentum=0.9)
            print(f"Create optimizer using lr with decay step. This is the initial learning rate: {optimizer.lr.numpy()}")
            print(f"This is the lr of the lr schedule when current step = decay steps: {float(lr_scheduler(self.lr_config.decay_steps))}")
            print(f"This is the min lr of the lr scheduler: {float(lr_scheduler(self.lr_config.decay_steps + 1))}")

        return optimizer


    def create_train_metric(self):
        return F1Score(name='train_acc_f1_score'), tf.keras.metrics.Mean(name='train_loss')

    def create_test_metric(self):
        return tf.keras.metrics.BinaryAccuracy(name='test_accuracy'), tf.keras.metrics.Mean(name='test_loss')

    def get_train_performance(self):
        return float(self.train_performance.result())

    def get_test_performance(self):
        return float(self.test_performance.result())

    def get_train_loss(self):
        return float(self.train_loss.result())

    def get_test_loss(self):
        return float(self.test_loss.result())

