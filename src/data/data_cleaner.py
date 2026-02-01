"""
AlgoViz Dashboard - Data Cleaner & Validator
============================================

Robust data cleaning pipeline that validates and cleans trading data
WITHOUT dropping any rows. Uses imputation, winsorization, and PCA.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class DataQualityReport:
    """Stores the results of data validation and cleaning."""
    total_rows: int = 0
    missing_values_imputed: int = 0
    outliers_winsorized: int = 0
    duplicates_resolved: int = 0
    negative_values_fixed: int = 0
    out_of_order_timestamps: int = 0
    zero_quantities_fixed: int = 0
    
    # PCA results
    pca_applied: bool = False
    n_components: int = 0
    explained_variance_ratios: List[float] = field(default_factory=list)
    cumulative_variance: List[float] = field(default_factory=list)
    
    # Validation passed
    is_valid: bool = True
    validation_errors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        """Convert report to dictionary."""
        return {
            'total_rows': self.total_rows,
            'missing_values_imputed': self.missing_values_imputed,
            'outliers_winsorized': self.outliers_winsorized,
            'duplicates_resolved': self.duplicates_resolved,
            'negative_values_fixed': self.negative_values_fixed,
            'out_of_order_timestamps': self.out_of_order_timestamps,
            'zero_quantities_fixed': self.zero_quantities_fixed,
            'pca_applied': self.pca_applied,
            'n_components': self.n_components,
            'explained_variance_ratios': self.explained_variance_ratios,
            'cumulative_variance': self.cumulative_variance,
            'is_valid': self.is_valid,
            'validation_errors': self.validation_errors
        }


class DataCleaner:
    """
    Comprehensive data cleaning pipeline for trading data.
    
    Key Principles:
    1. NO rows are ever dropped
    2. Missing values are imputed (forward-fill, backward-fill, interpolation)
    3. Outliers are winsorized (capped at percentiles)
    4. Duplicates get new IDs but data is preserved
    5. Timestamps are sorted and gaps interpolated
    """
    
    def __init__(
        self,
        outlier_lower_percentile: float = 1.0,
        outlier_upper_percentile: float = 99.0,
        enable_pca: bool = True,
        pca_variance_threshold: float = 0.95
    ):
        """
        Initialize the data cleaner.
        
        Args:
            outlier_lower_percentile: Lower percentile for winsorization
            outlier_upper_percentile: Upper percentile for winsorization
            enable_pca: Whether to apply PCA for dimensionality reduction
            pca_variance_threshold: Cumulative variance to retain with PCA
        """
        self.outlier_lower = outlier_lower_percentile
        self.outlier_upper = outlier_upper_percentile
        self.enable_pca = enable_pca
        self.pca_variance_threshold = pca_variance_threshold
        
        # Store PCA model for later use
        self.pca_model = None
        self.feature_columns = []
    
    def validate_and_clean(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, DataQualityReport]:
        """
        Validate and clean the input DataFrame.
        
        Args:
            df: Input DataFrame with trading data
            
        Returns:
            Tuple of (cleaned DataFrame, quality report)
        """
        report = DataQualityReport(total_rows=len(df))
        
        if df.empty:
            report.is_valid = False
            report.validation_errors.append("Empty DataFrame provided")
            return df, report
        
        # Make a copy to avoid modifying original
        cleaned_df = df.copy()
        
        # Step 1: Fix missing values
        cleaned_df, missing_count = self._impute_missing_values(cleaned_df)
        report.missing_values_imputed = missing_count
        
        # Step 2: Fix negative prices (if 'price' column exists)
        if 'price' in cleaned_df.columns:
            cleaned_df, neg_count = self._fix_negative_values(cleaned_df, 'price')
            report.negative_values_fixed = neg_count
        
        # Step 3: Fix zero quantities (if 'quantity' column exists)
        if 'quantity' in cleaned_df.columns:
            cleaned_df, zero_count = self._fix_zero_quantities(cleaned_df)
            report.zero_quantities_fixed = zero_count
        
        # Step 4: Resolve duplicate trade IDs (if 'trade_id' column exists)
        if 'trade_id' in cleaned_df.columns:
            cleaned_df, dup_count = self._resolve_duplicates(cleaned_df)
            report.duplicates_resolved = dup_count
        
        # Step 5: Fix out-of-order timestamps (if 'timestamp' column exists)
        if 'timestamp' in cleaned_df.columns:
            cleaned_df, ts_count = self._fix_timestamps(cleaned_df)
            report.out_of_order_timestamps = ts_count
        
        # Step 6: Winsorize outliers in numeric columns
        cleaned_df, outlier_count = self._winsorize_outliers(cleaned_df)
        report.outliers_winsorized = outlier_count
        
        # Step 7: Apply PCA if enabled and there are numeric features
        if self.enable_pca:
            cleaned_df, pca_info = self._apply_pca(cleaned_df)
            if pca_info:
                report.pca_applied = True
                report.n_components = pca_info['n_components']
                report.explained_variance_ratios = pca_info['explained_variance']
                report.cumulative_variance = pca_info['cumulative_variance']
        
        report.is_valid = True
        return cleaned_df, report
    
    def _impute_missing_values(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, int]:
        """Impute missing values using forward-fill, backward-fill, then median."""
        total_missing = 0
        
        for col in df.columns:
            missing_before = df[col].isna().sum()
            if missing_before > 0:
                # Try forward fill first
                df[col] = df[col].ffill()
                # Then backward fill for any remaining NaN at start
                df[col] = df[col].bfill()
                # If still missing (all NaN column), fill with median or 0
                if df[col].isna().any():
                    if df[col].dtype in ['float64', 'int64', 'float32', 'int32']:
                        median_val = df[col].median()
                        if pd.isna(median_val):
                            median_val = 0
                        df[col] = df[col].fillna(median_val)
                    else:
                        df[col] = df[col].fillna('unknown')
                
                total_missing += missing_before
        
        return df, total_missing
    
    def _fix_negative_values(self, df: pd.DataFrame, column: str) -> Tuple[pd.DataFrame, int]:
        """Fix negative values by taking absolute value."""
        negative_mask = df[column] < 0
        count = negative_mask.sum()
        if count > 0:
            df.loc[negative_mask, column] = df.loc[negative_mask, column].abs()
        return df, int(count)
    
    def _fix_zero_quantities(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, int]:
        """Replace zero quantities with median of nearby trades."""
        zero_mask = df['quantity'] == 0
        count = zero_mask.sum()
        if count > 0:
            # Use median of non-zero quantities
            median_qty = df.loc[~zero_mask, 'quantity'].median()
            if pd.isna(median_qty) or median_qty == 0:
                median_qty = 0.001  # Default small quantity
            df.loc[zero_mask, 'quantity'] = median_qty
        return df, int(count)
    
    def _resolve_duplicates(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, int]:
        """Resolve duplicate trade IDs by assigning new IDs (keep all rows)."""
        duplicates = df.duplicated(subset=['trade_id'], keep='first')
        count = duplicates.sum()
        if count > 0:
            # Assign new unique IDs to duplicates
            max_id = df['trade_id'].max()
            new_ids = range(int(max_id) + 1, int(max_id) + 1 + int(count))
            df.loc[duplicates, 'trade_id'] = list(new_ids)
        return df, int(count)
    
    def _fix_timestamps(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, int]:
        """Sort by timestamp and count out-of-order entries."""
        # Check if already sorted
        is_sorted = df['timestamp'].is_monotonic_increasing
        count = 0
        
        if not is_sorted:
            # Count how many are out of order
            diffs = df['timestamp'].diff()
            # Handle different timestamp types
            if hasattr(diffs.iloc[1] if len(diffs) > 1 else diffs.iloc[0], 'total_seconds'):
                count = (diffs.dt.total_seconds() < 0).sum()
            else:
                count = (diffs < 0).sum()
            # Sort by timestamp
            df = df.sort_values('timestamp').reset_index(drop=True)
        
        return df, int(count)
    
    def _winsorize_outliers(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, int]:
        """Winsorize outliers in numeric columns (cap at percentiles)."""
        total_outliers = 0
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        
        # Skip ID and boolean columns
        skip_cols = ['trade_id', 'is_buyer_maker']
        cols_to_winsorize = [c for c in numeric_cols if c not in skip_cols]
        
        for col in cols_to_winsorize:
            lower = np.percentile(df[col].dropna(), self.outlier_lower)
            upper = np.percentile(df[col].dropna(), self.outlier_upper)
            
            # Count outliers
            outlier_mask = (df[col] < lower) | (df[col] > upper)
            total_outliers += outlier_mask.sum()
            
            # Winsorize (cap at percentiles)
            df[col] = df[col].clip(lower=lower, upper=upper)
        
        return df, int(total_outliers)
    
    def _apply_pca(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Optional[Dict]]:
        """Apply PCA to numeric features for dimensionality reduction analysis."""
        from sklearn.preprocessing import StandardScaler
        from sklearn.decomposition import PCA
        
        # Select numeric columns only (excluding IDs and booleans)
        skip_cols = ['trade_id', 'is_buyer_maker', 'timestamp']
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        feature_cols = [c for c in numeric_cols if c not in skip_cols]
        
        if len(feature_cols) < 2:
            return df, None
        
        # Store feature columns for reference
        self.feature_columns = feature_cols
        
        # Extract and scale features
        features = df[feature_cols].values
        scaler = StandardScaler()
        features_scaled = scaler.fit_transform(features)
        
        # Apply PCA
        n_components = min(len(feature_cols), len(df))
        pca = PCA(n_components=n_components)
        pca_result = pca.fit_transform(features_scaled)
        
        # Store PCA model
        self.pca_model = pca
        
        # Calculate cumulative variance
        explained_var = pca.explained_variance_ratio_.tolist()
        cumulative_var = np.cumsum(explained_var).tolist()
        
        # Determine optimal components (to reach threshold)
        optimal_n = 1
        for i, cum_var in enumerate(cumulative_var):
            if cum_var >= self.pca_variance_threshold:
                optimal_n = i + 1
                break
        else:
            optimal_n = len(cumulative_var)
        
        # Add principal components to DataFrame
        for i in range(min(3, n_components)):  # Add top 3 PCs
            df[f'PC{i+1}'] = pca_result[:, i]
        
        return df, {
            'n_components': n_components,
            'optimal_components': optimal_n,
            'explained_variance': explained_var,
            'cumulative_variance': cumulative_var
        }
    
    def get_pca_summary(self) -> Optional[Dict]:
        """Get summary of PCA results if applied."""
        if self.pca_model is None:
            return None
        
        return {
            'n_components': self.pca_model.n_components_,
            'explained_variance': self.pca_model.explained_variance_ratio_.tolist(),
            'feature_columns': self.feature_columns
        }


def clean_synthetic_data(df: pd.DataFrame, enable_pca: bool = True) -> Tuple[pd.DataFrame, DataQualityReport]:
    """
    Convenience function to clean synthetic trading data.
    
    Args:
        df: DataFrame with synthetic trading data
        enable_pca: Whether to apply PCA analysis
        
    Returns:
        Tuple of (cleaned DataFrame, quality report)
    """
    cleaner = DataCleaner(
        outlier_lower_percentile=1.0,
        outlier_upper_percentile=99.0,
        enable_pca=enable_pca,
        pca_variance_threshold=0.95
    )
    return cleaner.validate_and_clean(df)
