import setuptools
setuptools.setup(
    name="asynfed",
    version="1.0.0",
    author="TTU SIT",
    description="asynfed lib",
    packages=setuptools.find_packages(),
    install_requires=[
        "boto3",
        "numpy",
        "pika",
        "python-dotenv",
        "tensorflow"
    ],
)
