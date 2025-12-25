import json
import joblib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from ..utils.logger import get_logger

logger = get_logger(__name__)


class ModelRegistry:
    """Registry for managing multiple model versions"""
    
    def __init__(self, registry_path: str = "models/registry"):
        self.registry_path = Path(registry_path)
        self.registry_path.mkdir(parents=True, exist_ok=True)
        self.metadata_file = self.registry_path / "registry.json"
        self.metadata = self._load_metadata()
    
    def _load_metadata(self) -> Dict:
        """Load registry metadata"""
        if self.metadata_file.exists():
            with open(self.metadata_file, 'r') as f:
                return json.load(f)
        return {'models': {}, 'active_model': None}
    
    def _save_metadata(self):
        """Save registry metadata"""
        with open(self.metadata_file, 'w') as f:
            json.dump(self.metadata, f, indent=2)
    
    def register_model(
        self,
        model: Any,
        model_name: str,
        model_type: str,
        metrics: Dict[str, float],
        hyperparameters: Dict[str, Any],
        description: str = ""
    ) -> str:
        """
        Register a new model version
        
        Args:
            model: Trained model object
            model_name: Name of the model
            model_type: Type of model (xgboost, random_forest, etc.)
            metrics: Performance metrics
            hyperparameters: Model hyperparameters
            description: Model description
            
        Returns:
            Model version ID
        """
        # Generate version ID
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        version_id = f"{model_name}_{timestamp}"
        
        logger.info(f"Registering model: {version_id}")
        
        # Save model file
        model_path = self.registry_path / f"{version_id}.pkl"
        joblib.dump(model, model_path)
        
        # Store metadata
        self.metadata['models'][version_id] = {
            'name': model_name,
            'type': model_type,
            'version': version_id,
            'registered_at': datetime.now().isoformat(),
            'metrics': metrics,
            'hyperparameters': hyperparameters,
            'description': description,
            'file_path': str(model_path),
            'status': 'registered'
        }
        
        # Set as active if it's the first model or has better performance
        if not self.metadata['active_model']:
            self.set_active_model(version_id)
        else:
            # Compare with active model
            active_metrics = self.metadata['models'][self.metadata['active_model']]['metrics']
            if metrics.get('auc_roc', 0) > active_metrics.get('auc_roc', 0):
                logger.info(f"New model {version_id} performs better. Setting as active.")
                self.set_active_model(version_id)
        
        self._save_metadata()
        
        logger.info(f"Model registered successfully: {version_id}")
        
        return version_id
    
    def load_model(self, version_id: Optional[str] = None) -> Any:
        """
        Load a model by version ID
        
        Args:
            version_id: Version ID (if None, loads active model)
            
        Returns:
            Loaded model object
        """
        if version_id is None:
            version_id = self.metadata['active_model']
            
        if not version_id:
            raise ValueError("No model specified and no active model set")
        
        if version_id not in self.metadata['models']:
            raise ValueError(f"Model {version_id} not found in registry")
        
        model_path = Path(self.metadata['models'][version_id]['file_path'])
        
        if not model_path.exists():
            raise FileNotFoundError(f"Model file not found: {model_path}")
        
        logger.info(f"Loading model: {version_id}")
        model = joblib.load(model_path)
        
        return model
    
    def set_active_model(self, version_id: str):
        """Set a model as the active production model"""
        if version_id not in self.metadata['models']:
            raise ValueError(f"Model {version_id} not found")
        
        # Update previous active model status
        if self.metadata['active_model']:
            self.metadata['models'][self.metadata['active_model']]['status'] = 'archived'
        
        # Set new active model
        self.metadata['active_model'] = version_id
        self.metadata['models'][version_id]['status'] = 'active'
        self.metadata['models'][version_id]['activated_at'] = datetime.now().isoformat()
        
        self._save_metadata()
        
        logger.info(f"Set active model: {version_id}")
    
    def get_active_model(self) -> Dict[str, Any]:
        """Get information about the active model"""
        if not self.metadata['active_model']:
            return None
        
        return self.metadata['models'][self.metadata['active_model']]
    
    def list_models(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all models in registry
        
        Args:
            status: Filter by status (active, archived, registered)
            
        Returns:
            List of model metadata
        """
        models = list(self.metadata['models'].values())
        
        if status:
            models = [m for m in models if m['status'] == status]
        
        # Sort by registration date (newest first)
        models.sort(key=lambda x: x['registered_at'], reverse=True)
        
        return models
    
    def compare_models(self, version_ids: List[str]) -> Dict[str, Any]:
        """
        Compare multiple models
        
        Args:
            version_ids: List of version IDs to compare
            
        Returns:
            Comparison dictionary
        """
        comparison = {
            'models': [],
            'best_model': None,
            'best_metric': 0
        }
        
        for version_id in version_ids:
            if version_id not in self.metadata['models']:
                logger.warning(f"Model {version_id} not found")
                continue
            
            model_info = self.metadata['models'][version_id]
            comparison['models'].append({
                'version': version_id,
                'type': model_info['type'],
                'metrics': model_info['metrics'],
                'registered_at': model_info['registered_at']
            })
            
            # Track best model
            auc_score = model_info['metrics'].get('auc_roc', 0)
            if auc_score > comparison['best_metric']:
                comparison['best_metric'] = auc_score
                comparison['best_model'] = version_id
        
        return comparison
    
    def delete_model(self, version_id: str, force: bool = False):
        """
        Delete a model from registry
        
        Args:
            version_id: Version ID to delete
            force: Force delete even if active
        """
        if version_id not in self.metadata['models']:
            raise ValueError(f"Model {version_id} not found")
        
        # Prevent deletion of active model unless forced
        if version_id == self.metadata['active_model'] and not force:
            raise ValueError(
                f"Cannot delete active model {version_id}. "
                "Set a different active model first or use force=True"
            )
        
        # Delete model file
        model_path = Path(self.metadata['models'][version_id]['file_path'])
        if model_path.exists():
            model_path.unlink()
        
        # Remove from metadata
        del self.metadata['models'][version_id]
        
        # Clear active model if this was it
        if version_id == self.metadata['active_model']:
            self.metadata['active_model'] = None
        
        self._save_metadata()
        
        logger.info(f"Deleted model: {version_id}")
    
    def export_model_info(self, version_id: str, output_file: str):
        """Export model information to JSON file"""
        if version_id not in self.metadata['models']:
            raise ValueError(f"Model {version_id} not found")
        
        model_info = self.metadata['models'][version_id]
        
        with open(output_file, 'w') as f:
            json.dump(model_info, f, indent=2)
        
        logger.info(f"Exported model info to {output_file}")


if __name__ == "__main__":
    # Example usage
    registry = ModelRegistry()
    
    # List all models
    models = registry.list_models()
    print(f"Total models in registry: {len(models)}")
    
    # Get active model
    active = registry.get_active_model()
    if active:
        print(f"\nActive model: {active['version']}")
        print(f"AUC-ROC: {active['metrics'].get('auc_roc', 0):.4f}")