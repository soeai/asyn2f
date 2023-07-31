'''
ResNet18/34/50/101/152 in TensorFlow2.

Reference:
[1] He, Kaiming, et al.
    "Deep residual learning for image recognition."
    Proceedings of the IEEE conference on computer vision and pattern recognition. 2016.
'''
import tensorflow as tf

class BasicBlock(tf.keras.Model):
    expansion = 1
    
    def __init__(self, in_channels, out_channels, strides=1):
        super(BasicBlock, self).__init__()
        self.conv1 = tf.keras.layers.Conv2D(out_channels, kernel_size=3, strides=strides, padding='same', use_bias=False)
        self.bn1 = tf.keras.layers.BatchNormalization()
        self.conv2 = tf.keras.layers.Conv2D(out_channels, kernel_size=3, strides=1, padding='same', use_bias=False)
        self.bn2 = tf.keras.layers.BatchNormalization()
        
        if strides != 1 or in_channels != self.expansion*out_channels:
            self.shortcut = tf.keras.Sequential([
                tf.keras.layers.Conv2D(self.expansion*out_channels, kernel_size=1, strides=strides, use_bias=False), 
                tf.keras.layers.BatchNormalization()
            ])
        else:
            self.shortcut = lambda x: x
            
    def call(self, x):
        out = tf.keras.activations.relu(self.bn1(self.conv1(x)))
        out = self.bn2(self.conv2(out))
        out = tf.keras.layers.add([self.shortcut(x), out])
        out = tf.keras.activations.relu(out)
        return out


class Resnet18(Model):
    def __init__(self, num_classes: int = 10):
        super(Resnet18, self).__init__()
        self.in_channels = 64
        
        block = BasicBlock
        num_blocks = [2, 2, 2, 2]

        self.conv1 = tf.keras.layers.Conv2D(64, kernel_size=3, strides=1, padding='same', use_bias=False)
        self.bn1 = tf.keras.layers.BatchNormalization()
        self.layer1 = self._make_layer(block, 64, num_blocks[0], strides=1)
        self.layer2 = self._make_layer(block, 128, num_blocks[1], strides=2)
        self.layer3 = self._make_layer(block, 256, num_blocks[2], strides=2)
        self.layer4 = self._make_layer(block, 512, num_blocks[3], strides=2)
        self.avg_pool2d = tf.keras.layers.AveragePooling2D(pool_size=4)
        self.flatten = tf.keras.layers.Flatten()
        self.fc = tf.keras.layers.Dense(num_classes, activation='softmax')
    
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
    
    def _make_layer(self, block, out_channels, num_blocks, strides):
        stride = [strides] + [1]*(num_blocks-1)
        layer = []
        for s in stride:
            layer += [block(self.in_channels, out_channels, s)]
            self.in_channels = out_channels * block.expansion
        return tf.keras.Sequential(layer)


