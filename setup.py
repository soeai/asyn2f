import setuptools
setuptools.setup(
    name="fedasync",
    version="1.0.0",
    author="TTU SOE",
    description="fedasync lib",
    packages=setuptools.find_packages(),
    install_requires=[
        "boto3",
        "numpy",
        "pika",
        "python-dotenv",
        "tensorflow"
    ],
)
