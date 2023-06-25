import pandas as pd
import numpy as np


def class_overlap_calculator(df: pd.DataFrame):
    from imblearn.under_sampling import TomekLinks

    X = df.iloc[:, :-1].values  # Features
    y = df.iloc[:, -1].values  # Labels

    tl = TomekLinks()
    X_res, y_res = tl.fit_resample(X, y)

    # Compute Class Overlap
    overlap = (len(y) - len(y_res)) / len(y)

    return overlap



def class_parity_calculator(df: pd.DataFrame):
    # Assuming df is your DataFrame and it's already defined
    X = df.iloc[:, :-1].values  # Features
    y = df.iloc[:, -1].values  # Labels

    # Compute the relative size of each class
    unique_classes, counts = np.unique(y, return_counts=True)
    relative_sizes = counts / counts.max()

    # Compute the mean of the relative sizes
    mean_relative_size = np.mean(relative_sizes)

    # Compute Class Parity
    class_parity = 1 - np.sum(np.abs(relative_sizes - mean_relative_size)) / len(unique_classes)

    return class_parity


def label_purity_calculator(df: pd.DataFrame):
    from imblearn.under_sampling import TomekLinks
    from cleanlab.pruning import get_noise_indices

    X = df.iloc[:, :-1].values  # Features
    y = df.iloc[:, -1].values  # Labels

    # Find indices of Tomek Links
    tl = TomekLinks(return_indices=True)
    X_res, y_res, id_tl = tl.fit_resample(X, y)

    # Find indices of noisy (problematic) labels
    psx = np.ones((len(y), len(np.unique(y)))) / len(np.unique(y))  # uniform prior over labels
    _, id_noise = get_noise_indices(y, psx)

    # Compute intersection of Tomek Links and noisy labels
    impure_indices = np.intersect1d(id_tl, id_noise)

    # Compute Label Purity
    label_purity = 1 - len(impure_indices) / len(y)

    return label_purity


def feature_correlation_calculator(df: pd.DataFrame):
    X = df.iloc[:, :-1]  # Features

    # Compute the correlation matrix
    corr_matrix = X.corr().abs()

    # Since we're considering all pairs (i,j), we don't need to mask the lower triangle
    total_corr = corr_matrix.sum().sum() - corr_matrix.trace()  # subtract main diagonal (self-correlations)
    
    # Normalize by the number of feature pairs
    num_features = len(df.columns) - 1  # exclude label column
    total_pairs = num_features ** 2

    # Compute Feature Correlation
    feature_corr = 1 - total_corr / total_pairs

    return feature_corr


def feature_relevance_calculator(df: pd.DataFrame, alpha: float, beta: float):
    from sklearn.tree import DecisionTreeClassifier
    X = df.iloc[:, :-1]  # Features
    y = df.iloc[:, -1]  # Labels

    # Train a DecisionTreeClassifier to get feature importances
    dt = DecisionTreeClassifier(random_state=0)
    dt.fit(X, y)
    feature_importances = dt.feature_importances_

    # Compute variance of feature importances
    fi_variance = np.var(feature_importances)

    # Compute mean of top 3 feature importances
    top_3_mean = np.mean(sorted(feature_importances, reverse=True)[:3])

    # Compute Feature Relevance
    feature_relevance = alpha * (1 - fi_variance) + beta * top_3_mean

    return feature_relevance

def completeness_calculator(df: pd.DataFrame):
    # Count total null values in the DataFrame
    total_null = df.isnull().sum().sum()
    
    # Calculate total entries in the DataFrame
    total_entries = np.product(df.shape)

    # Compute Completeness
    completeness = 1 - total_null / total_entries

    return completeness