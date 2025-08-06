import pandas as pd
import datetime as dt

def load_data(filepath):
    """
    Loads data from a CSV file into a pandas DataFrame.

    Args:
        filepath (str): The path to the CSV file.

    Returns:
        pd.DataFrame: The loaded DataFrame.
    """
    try:
        df = pd.read_csv(filepath)
        print("Data loaded successfully.")
        return df
    except FileNotFoundError:
        print(f"Error: The file at {filepath} was not found.")
        return None

def clean_data(df):
    """
    Performs initial cleaning on the raw transactional data.

    This function handles:
    - Dropping rows with missing CustomerID.
    - Removing duplicate rows.
    - Correcting data types for CustomerID.
    - Cleaning the UnitPrice column by removing currency symbols and converting to float.
    - Removing cancelled orders (InvoiceNo starting with 'C').
    - Filtering out transactions with negative quantity.

    Args:
        df (pd.DataFrame): The raw DataFrame.

    Returns:
        pd.DataFrame: The cleaned DataFrame.
    """
    # --- Handle Missing Values ---
    # Drop rows where CustomerID is null, as they are not useful for segmentation.
    df.dropna(axis=0, subset=['CustomerID'], inplace=True)
    print(f"Removed rows with missing CustomerID. New shape: {df.shape}")

    # --- Handle Duplicates ---
    df.drop_duplicates(inplace=True)
    print(f"Removed duplicate rows. New shape: {df.shape}")

    # --- Correct Data Types ---
    # Convert CustomerID to integer
    df['CustomerID'] = df['CustomerID'].astype(int)

    # Clean and convert UnitPrice to a numeric type
    # Replace currency symbols and convert to float
    if df['UnitPrice'].dtype == 'object':
        df['UnitPrice'] = df['UnitPrice'].str.replace('[£,]', '', regex=True).astype(float)
    
    # --- Handle Cancellations ---
    # Remove rows where InvoiceNo starts with 'C' (cancellations)
    df = df[~df['InvoiceNo'].astype(str).str.startswith('C')]
    # Remove any rows where quantity is zero or negative
    df = df[df['Quantity'] > 0]
    print(f"Removed cancellations and negative quantities. Final shape: {df.shape}")
    
    return df

def preprocess_data(df):
    """
    Performs data preprocessing steps necessary for RFM calculation.

    This function handles:
    - Converting InvoiceDate to datetime objects.
    - Calculating TotalPrice.

    Args:
        df (pd.DataFrame): The cleaned DataFrame.

    Returns:
        pd.DataFrame: The preprocessed DataFrame.
    """
    # --- Convert InvoiceDate to datetime ---
    # The 'errors="coerce"' will turn unparseable dates into NaT (Not a Time)
    df['InvoiceDate'] = pd.to_datetime(df['InvoiceDate'], errors='coerce')
    # Drop any rows that had unparseable dates
    df.dropna(subset=['InvoiceDate'], inplace=True)
    
    # --- Calculate TotalPrice ---
    df['TotalPrice'] = df['Quantity'] * df['UnitPrice']
    print("Calculated TotalPrice column.")
    
    return df

def calculate_rfm(df):
    """
    Calculates Recency, Frequency, and Monetary values for each customer.

    Args:
        df (pd.DataFrame): The preprocessed DataFrame with a 'TotalPrice' column.

    Returns:
        pd.DataFrame: A DataFrame with CustomerID and their R, F, M values.
    """
    # --- Set a snapshot date for recency calculation ---
    # This is typically the day after the last transaction in the dataset.
    snapshot_date = df['InvoiceDate'].max() + dt.timedelta(days=1)
    print(f"Snapshot date for Recency calculation: {snapshot_date.date()}")

    # --- Calculate RFM metrics ---
    rfm_df = df.groupby('CustomerID').agg({
        'InvoiceDate': lambda date: (snapshot_date - date.max()).days,
        'InvoiceNo': 'nunique',
        'TotalPrice': 'sum'
    })

    # --- Rename columns for clarity ---
    rfm_df.rename(columns={'InvoiceDate': 'Recency',
                           'InvoiceNo': 'Frequency',
                           'TotalPrice': 'MonetaryValue'}, inplace=True)
                           
    print("RFM values calculated successfully.")
    return rfm_df

def assign_rfm_scores(rfm_df):
    """
    Assigns scores from 1 to 5 to each RFM metric.
    
    For Recency, lower values are better (more recent).
    For Frequency and Monetary, higher values are better.

    Args:
        rfm_df (pd.DataFrame): DataFrame with Recency, Frequency, MonetaryValue.

    Returns:
        pd.DataFrame: The RFM DataFrame with R, F, and M score columns.
    """
    # The qcut function divides the data into equal-sized bins (quintiles in this case)
    rfm_df['R_Score'] = pd.qcut(rfm_df['Recency'], 5, labels=[5, 4, 3, 2, 1])
    rfm_df['F_Score'] = pd.qcut(rfm_df['Frequency'].rank(method='first'), 5, labels=[1, 2, 3, 4, 5])
    rfm_df['M_Score'] = pd.qcut(rfm_df['MonetaryValue'], 5, labels=[1, 2, 3, 4, 5])
    
    print("RFM scores assigned.")
    return rfm_df
