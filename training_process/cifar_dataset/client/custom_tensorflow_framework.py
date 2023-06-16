
# import os
# import sys
# root = os.path.dirname(os.path.dirname(os.path.dirname(os.getcwd())))
# sys.path.append(root)

import tensorflow as tf
from tensorflow.keras import Model
from asynfed.client.frameworks.tensorflow.tensorflow_framework import TensorflowFramework
'''
    - This is a reference of how user can defined a tensorflow model
        that can be used in our platform
    - users can use our abstract class to define their own model
        or they can design one by themselves
        as long as it is inherited from class ModelWarapper
        and satify all the requirements (at least provide data_size, train_ds, and 
        implement of all abstract functions)
    - more frameworks can be found at asynfed/client/frameworks directory
'''

class CustomTensorflowFramework(TensorflowFramework):
    # Tensorflow Model must be an inheritant of class tensorflow.keras.Model
    # model, data_size, train_ds is required
    # test_ds is optional
    def __init__(self, model: Model, epoch: int = 5, data_size: int = 10, qod: float = 0.9, train_ds = None, test_ds = None, delta_time: int = 15):
        super().__init__(model = model, epoch = epoch, data_size = data_size, qod = qod, train_ds = train_ds, test_ds = test_ds, delta_time= delta_time)

    @tf.function
    def train_step(self, images, labels):
        with tf.GradientTape() as tape:
            # training=True is only needed if there are layers with different
            # behavior during training versus inference (e.g. Dropout).
            predictions = self.model(images, training=True)
            # predictions = self.model(images)
            loss = self.model.loss_object(labels, predictions)

        gradients = tape.gradient(loss, self.model.trainable_variables)
        self.model.optimizer.apply_gradients(zip(gradients, self.model.trainable_variables))
        self.model.train_loss(loss)
        self.model.train_performance(labels, predictions)


# for epoch in range(100):
#     print(f'Start of epoch {epoch+1}')

#     # Set learning rate for this epoch
#     lr = lr_scheduler(epoch, model.optimizer.learning_rate)
#     model.optimizer.learning_rate = lr

#     # Iterate over the batches of the dataset.
#     for step, (x_batch_train, y_batch_train) in enumerate(train_dataset):

#         # Perform forward and backward pass
#         logs = model.train_step([x_batch_train, y_batch_train])

#         # Log metrics
#         if step % 200 == 0:
#             print(f'Training loss (for one batch) at step {step}: {logs["loss"]}')
#             print(f'Seen so far: {(step + 1) * 64} samples')

#     # Save weights every 10 epochs
#     if (epoch + 1) % 10 == 0:
#         model.save_weights(f'./weights_{epoch+1}.h5')
