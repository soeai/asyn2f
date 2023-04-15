import tensorflow as tf
from tensorflow.keras import Model
from tensorflow.keras.layers import Dense, Flatten, Conv2D, AveragePooling2D


class LeNet(Model):
    def __init__(self, input_shape=(32, 32, 1), nb_classes=10):
        super().__init__()
        self.create_model(input_shape = input_shape, nb_classes = nb_classes)
        # loss
        self.loss_object = None
        # optimizer
        self.optimizer = None
        # metric
        self.train_loss = None
        self.train_accuracy = None
        self.test_loss = None
        self.test_accuracy = None
        # create these objects by calling compile method
        self.compile()

        # variable for training process
        self.previous_weights = None
        self.current_weights = None
        self.global_weights = None
        self.direction = None
        self.merged_result = None


        
    def create_model(self, input_shape, nb_classes):
        self.conv1 = Conv2D(6, kernel_size=(5, 5), strides=(1, 1), activation='tanh', input_shape=input_shape, padding="valid")
        self.avgpool1 = AveragePooling2D(pool_size=(2, 2), strides=(2, 2), padding='valid')
        self.conv2 = Conv2D(16, kernel_size=(5, 5), strides=(1, 1), activation='tanh', padding='valid')
        self.avgpool2 = AveragePooling2D(pool_size=(2, 2), strides=(2, 2), padding='valid')
        self.flatten = Flatten()
        self.dense1 = Dense(120, activation='tanh')
        self.dense2 = Dense(84, activation='tanh')
        self.dense3 = Dense(nb_classes, activation='softmax')
        

    def call(self, x):
        x = self.conv1(x)
        x = self.avgpool1(x)
        x = self.conv2(x)
        x = self.avgpool2(x)
        x = self.flatten(x)
        x = self.dense1(x)
        x = self.dense2(x)
        x = self.dense3(x)
        return x
    
    def compile(self, loss = "categorical_crossentropy", optimizer = "Adam", metric = "accuracy"):
        # Now, for this model, support only this set of choice 
        if loss == "categorical_crossentropy":
        # define loss = Categorical Crossentropy
            self.loss_object = tf.keras.losses.SparseCategoricalCrossentropy(from_logits=True)
        if optimizer == "Adam":
        # define optimizer = Adam
            self.optimizer = tf.keras.optimizers.Adam()
        if metric == "accuracy":
            # setting up metric = accuracy
            self.train_loss = tf.keras.metrics.Mean(name='train_loss')
            self.train_accuracy = tf.keras.metrics.SparseCategoricalAccuracy(name='train_accuracy')
            self.test_loss = tf.keras.metrics.Mean(name='test_loss')
            self.test_accuracy = tf.keras.metrics.SparseCategoricalAccuracy(name='test_accuracy')

    def set_pretrained_weights(self, weights, train_ds):
        num_of_layers= len(self.get_weights())
        if num_of_layers < len(weights):
            for images, labels in train_ds:
                self.train_step(images, labels)
                break
        self.set_weights(weights)


    @tf.function
    def test_step(self, images, labels):
        # training=False is only needed if there are layers with different
        # behavior during training versus inference (e.g. Dropout).
        predictions = self(images, training=False)
        t_loss = self.loss_object(labels, predictions)
        self.test_loss(t_loss)
        self.test_accuracy(labels, predictions)
        
    @tf.function
    def train_step(self, images, labels):
        with tf.GradientTape() as tape:
        # training=True is only needed if there are layers with different
        # behavior during training versus inference (e.g. Dropout).
            predictions = self(images, training=True)
            loss = self.loss_object(labels, predictions)
        # compute the gradient based on the loss
        gradients = tape.gradient(loss, self.trainable_variables)
        # update the weights based on some formula determined by the chosen algorithm
        self.optimizer.apply_gradients(zip(gradients, self.trainable_variables))
        # update training info
        self.train_loss(loss)
        self.train_accuracy(labels, predictions)

