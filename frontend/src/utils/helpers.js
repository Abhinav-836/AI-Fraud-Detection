/**
 * Utility Helper Functions for Fraud Detection Frontend
 * Location: frontend/src/utils/helpers.js
 */

/**
 * Format a number as currency
 * @param {number} amount - The amount to format
 * @param {string} currency - Currency code (default: USD)
 * @returns {string} Formatted currency string
 */
export const formatCurrency = (amount, currency = 'USD') => {
    if (amount === null || amount === undefined) return 'N/A';
    
    const formatter = new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency,
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
    
    return formatter.format(amount);
  };
  
  /**
   * Format a date string or Date object
   * @param {string|Date} date - Date to format
   * @param {boolean} includeTime - Whether to include time (default: true)
   * @returns {string} Formatted date string
   */
  export const formatDate = (date, includeTime = true) => {
    if (!date) return 'N/A';
    
    const dateObj = typeof date === 'string' ? new Date(date) : date;
    
    if (isNaN(dateObj.getTime())) return 'Invalid Date';
    
    if (includeTime) {
      return dateObj.toLocaleString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      });
    }
    
    return dateObj.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };
  
  /**
   * Calculate risk level color based on probability or risk level
   * @param {string|number} risk - Risk level string or probability number
   * @returns {string} Color code
   */
  export const calculateRiskColor = (risk) => {
    if (typeof risk === 'number') {
      // If it's a probability (0-1)
      if (risk >= 0.7) return '#f44336'; // Red - High risk
      if (risk >= 0.4) return '#ff9800'; // Orange - Medium risk
      return '#4caf50'; // Green - Low risk
    }
    
    // If it's a string (low, medium, high)
    const riskLevel = risk?.toLowerCase();
    
    switch (riskLevel) {
      case 'high':
        return '#f44336'; // Red
      case 'medium':
        return '#ff9800'; // Orange
      case 'low':
        return '#4caf50'; // Green
      default:
        return '#9e9e9e'; // Gray
    }
  };
  
  /**
   * Get risk level badge style
   * @param {string} riskLevel - Risk level (low, medium, high)
   * @returns {Object} Style object for badge
   */
  export const getRiskBadgeStyle = (riskLevel) => {
    const color = calculateRiskColor(riskLevel);
    
    return {
      backgroundColor: color,
      color: 'white',
      padding: '4px 12px',
      borderRadius: '12px',
      fontSize: '12px',
      fontWeight: 'bold',
      display: 'inline-block',
      textTransform: 'uppercase',
    };
  };
  
  /**
   * Format percentage
   * @param {number} value - Value between 0 and 1
   * @param {number} decimals - Number of decimal places (default: 1)
   * @returns {string} Formatted percentage
   */
  export const formatPercentage = (value, decimals = 1) => {
    if (value === null || value === undefined) return 'N/A';
    return `${(value * 100).toFixed(decimals)}%`;
  };
  
  /**
   * Truncate text to specified length
   * @param {string} text - Text to truncate
   * @param {number} maxLength - Maximum length (default: 50)
   * @returns {string} Truncated text
   */
  export const truncateText = (text, maxLength = 50) => {
    if (!text) return '';
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
  };
  
  /**
   * Get fraud status icon
   * @param {boolean} isFraud - Whether transaction is fraudulent
   * @returns {string} Icon emoji
   */
  export const getFraudIcon = (isFraud) => {
    return isFraud ? '🚨' : '✅';
  };
  
  /**
   * Format transaction ID
   * @param {string} transactionId - Transaction ID
   * @returns {string} Formatted transaction ID
   */
  export const formatTransactionId = (transactionId) => {
    if (!transactionId) return 'N/A';
    
    // If transaction ID is long, show first 8 and last 4 characters
    if (transactionId.length > 20) {
      return `${transactionId.substring(0, 8)}...${transactionId.substring(transactionId.length - 4)}`;
    }
    
    return transactionId;
  };
  
  /**
   * Calculate time ago
   * @param {string|Date} date - Date to calculate from
   * @returns {string} Time ago string (e.g., "2 hours ago")
   */
  export const timeAgo = (date) => {
    if (!date) return 'N/A';
    
    const dateObj = typeof date === 'string' ? new Date(date) : date;
    const seconds = Math.floor((new Date() - dateObj) / 1000);
    
    const intervals = {
      year: 31536000,
      month: 2592000,
      week: 604800,
      day: 86400,
      hour: 3600,
      minute: 60,
      second: 1,
    };
    
    for (const [unit, secondsInUnit] of Object.entries(intervals)) {
      const interval = Math.floor(seconds / secondsInUnit);
      
      if (interval >= 1) {
        return `${interval} ${unit}${interval === 1 ? '' : 's'} ago`;
      }
    }
    
    return 'just now';
  };
  
  /**
   * Validate transaction amount
   * @param {number} amount - Amount to validate
   * @returns {Object} Validation result {isValid, message}
   */
  export const validateAmount = (amount) => {
    if (!amount || amount <= 0) {
      return { isValid: false, message: 'Amount must be greater than 0' };
    }
    
    if (amount > 1000000) {
      return { isValid: false, message: 'Amount exceeds maximum limit' };
    }
    
    return { isValid: true, message: '' };
  };
  
  /**
   * Get confidence level description
   * @param {number} confidence - Confidence value (0-1)
   * @returns {string} Description
   */
  export const getConfidenceDescription = (confidence) => {
    if (confidence >= 0.9) return 'Very High';
    if (confidence >= 0.7) return 'High';
    if (confidence >= 0.5) return 'Medium';
    if (confidence >= 0.3) return 'Low';
    return 'Very Low';
  };
  
  /**
   * Sort array by field
   * @param {Array} array - Array to sort
   * @param {string} field - Field to sort by
   * @param {string} order - Sort order ('asc' or 'desc')
   * @returns {Array} Sorted array
   */
  export const sortBy = (array, field, order = 'asc') => {
    return [...array].sort((a, b) => {
      const aVal = a[field];
      const bVal = b[field];
      
      if (aVal < bVal) return order === 'asc' ? -1 : 1;
      if (aVal > bVal) return order === 'asc' ? 1 : -1;
      return 0;
    });
  };
  
  /**
   * Filter transactions by criteria
   * @param {Array} transactions - Array of transactions
   * @param {Object} filters - Filter criteria
   * @returns {Array} Filtered transactions
   */
  export const filterTransactions = (transactions, filters) => {
    return transactions.filter(transaction => {
      // Filter by fraud status
      if (filters.isFraud !== undefined && transaction.is_fraud !== filters.isFraud) {
        return false;
      }
      
      // Filter by risk level
      if (filters.riskLevel && transaction.risk_level !== filters.riskLevel.toLowerCase()) {
        return false;
      }
      
      // Filter by amount range
      if (filters.minAmount && transaction.amount < filters.minAmount) {
        return false;
      }
      if (filters.maxAmount && transaction.amount > filters.maxAmount) {
        return false;
      }
      
      // Filter by search term (transaction ID)
      if (filters.searchTerm) {
        const searchLower = filters.searchTerm.toLowerCase();
        if (!transaction.transaction_id?.toLowerCase().includes(searchLower)) {
          return false;
        }
      }
      
      return true;
    });
  };
  
  /**
   * Calculate statistics from transactions
   * @param {Array} transactions - Array of transactions
   * @returns {Object} Statistics object
   */
  export const calculateStats = (transactions) => {
    if (!transactions || transactions.length === 0) {
      return {
        total: 0,
        fraudCount: 0,
        fraudRate: 0,
        totalAmount: 0,
        averageAmount: 0,
        highRiskCount: 0,
      };
    }
    
    const fraudCount = transactions.filter(t => t.is_fraud).length;
    const totalAmount = transactions.reduce((sum, t) => sum + (t.amount || 0), 0);
    const highRiskCount = transactions.filter(t => t.risk_level === 'high').length;
    
    return {
      total: transactions.length,
      fraudCount,
      fraudRate: fraudCount / transactions.length,
      totalAmount,
      averageAmount: totalAmount / transactions.length,
      highRiskCount,
    };
  };
  
  /**
   * Export transactions to CSV
   * @param {Array} transactions - Array of transactions
   * @param {string} filename - Output filename
   */
  export const exportToCSV = (transactions, filename = 'transactions.csv') => {
    if (!transactions || transactions.length === 0) {
      alert('No transactions to export');
      return;
    }
    
    // Get headers from first transaction
    const headers = Object.keys(transactions[0]);
    
    // Create CSV content
    const csvContent = [
      headers.join(','),
      ...transactions.map(transaction =>
        headers.map(header => {
          const value = transaction[header];
          // Escape commas and quotes
          if (typeof value === 'string' && (value.includes(',') || value.includes('"'))) {
            return `"${value.replace(/"/g, '""')}"`;
          }
          return value;
        }).join(',')
      )
    ].join('\n');
    
    // Create download link
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    
    link.setAttribute('href', url);
    link.setAttribute('download', filename);
    link.style.visibility = 'hidden';
    
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };
  
  /**
   * Copy text to clipboard
   * @param {string} text - Text to copy
   * @returns {Promise<boolean>} Success status
   */
  export const copyToClipboard = async (text) => {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch (err) {
      console.error('Failed to copy:', err);
      return false;
    }
  };
  
  // Export all functions as default object as well
  export default {
    formatCurrency,
    formatDate,
    calculateRiskColor,
    getRiskBadgeStyle,
    formatPercentage,
    truncateText,
    getFraudIcon,
    formatTransactionId,
    timeAgo,
    validateAmount,
    getConfidenceDescription,
    sortBy,
    filterTransactions,
    calculateStats,
    exportToCSV,
    copyToClipboard,
  };