"""
Configuration Validation Utilities - Prevents configuration-related bugs
"""

import logging
import json
import os
from typing import Dict, Any, List, Optional, Union, Type
from dataclasses import dataclass
from datetime import datetime

@dataclass
class ValidationResult:
    """Configuration validation result"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    field_validations: Dict[str, bool]

class ConfigValidator:
    """Comprehensive configuration validation"""
    
    def __init__(self):
        self.logger = logging.getLogger("config_validator")
        self.type_validators = {}
        self.field_validators = {}
        
        # Register default validators
        self._register_default_validators()
        
    def validate_config(self, config: Dict[str, Any], schema: Dict[str, Any] = None) -> ValidationResult:
        """Validate entire configuration"""
        try:
            errors = []
            warnings = []
            field_validations = {}
            
            # Use schema if provided
            if schema:
                for field_name, field_schema in schema.items():
                    is_valid, field_errors = self._validate_field(
                        field_name, 
                        config.get(field_name), 
                        field_schema
                    )
                    
                    field_validations[field_name] = is_valid
                    
                    if not is_valid:
                        errors.extend(field_errors)
            else:
                # Validate without schema
                for field_name, value in config.items():
                    is_valid, field_errors = self._validate_field_generic(field_name, value)
                    
                    field_validations[field_name] = is_valid
                    
                    if not is_valid:
                        errors.extend(field_errors)
                        
            return ValidationResult(
                is_valid=len(errors) == 0,
                errors=errors,
                warnings=warnings,
                field_validations=field_validations
            )
            
        except Exception as e:
            self.logger.error(f"Error validating config: {e}")
            return ValidationResult(False, [str(e)], [], {})
            
    def validate_field(self, field_name: str, value: Any, field_schema: Dict[str, Any]) -> tuple[bool, List[str]]:
        """Validate individual field"""
        try:
            errors = []
            
            # Check required fields
            if field_schema.get("required", False) and value is None:
                errors.append(f"Required field '{field_name}' is missing")
                return False, errors
                
            # Skip validation if field is optional and None
            if value is None and not field_schema.get("required", False):
                return True, []
                
            # Type validation
            expected_type = field_schema.get("type")
            if expected_type and not self._validate_type(value, expected_type):
                errors.append(f"Field '{field_name}' should be of type {expected_type.__name__}, got {type(value).__name__}")
                
            # Range validation
            min_val = field_schema.get("min")
            max_val = field_schema.get("max")
            if min_val is not None and not self._validate_range(value, min_val, max_val):
                errors.append(f"Field '{field_name}' should be between {min_val} and {max_val}")
                
            # Choice validation
            choices = field_schema.get("choices")
            if choices and value not in choices:
                errors.append(f"Field '{field_name}' must be one of {choices}, got '{value}'")
                
            # Pattern validation
            pattern = field_schema.get("pattern")
            if pattern and not self._validate_pattern(value, pattern):
                errors.append(f"Field '{field_name}' does not match required pattern")
                
            # Custom validator
            validator = field_schema.get("validator")
            if validator:
                try:
                    if not validator(value):
                        errors.append(f"Field '{field_name}' failed custom validation")
                except Exception as e:
                    errors.append(f"Custom validator error for '{field_name}': {e}")
                    
            return len(errors) == 0, errors
            
        except Exception as e:
            self.logger.error(f"Error validating field {field_name}: {e}")
            return False, [str(e)]
            
    def _validate_field_generic(self, field_name: str, value: Any) -> tuple[bool, List[str]]:
        """Validate field without schema"""
        try:
            errors = []
            
            # Basic type checks
            if isinstance(value, (list, dict)):
                # Validate nested structures
                if isinstance(value, dict):
                    for key, val in value.items():
                        is_valid, field_errors = self._validate_field_generic(f"{field_name}.{key}", val)
                        if not is_valid:
                            errors.extend(field_errors)
                elif isinstance(value, list):
                    for i, val in enumerate(value):
                        is_valid, field_errors = self._validate_field_generic(f"{field_name}[{i}]", val)
                        if not is_valid:
                            errors.extend(field_errors)
                            
            return len(errors) == 0, errors
            
        except Exception as e:
            self.logger.error(f"Error in generic field validation: {e}")
            return False, [str(e)]
            
    def _validate_type(self, value: Any, expected_type: Type) -> bool:
        """Validate type with special handling"""
        try:
            # Handle Union types
            if hasattr(expected_type, '__origin__'):
                # This is a Union type
                origin_types = expected_type.__origin__
                return any(isinstance(value, t) for t in origin_types)
                
            # Handle Optional types
            if hasattr(expected_type, '__origin__') and expected_type.__origin__ is Union:
                origin_types = expected_type.__args__
                return value is None or any(isinstance(value, t) for t in origin_types)
                
            # Regular type check
            return isinstance(value, expected_type)
            
        except Exception:
            return False
            
    def _validate_range(self, value: Any, min_val: Any, max_val: Any) -> bool:
        """Validate numeric range"""
        try:
            if isinstance(value, (int, float)):
                return min_val <= value <= max_val
            return False
            
        except Exception:
            return False
            
    def _validate_pattern(self, value: str, pattern: str) -> bool:
        """Validate string pattern"""
        try:
            import re
            return bool(re.match(pattern, value))
            
        except Exception:
            return False
            
    def _register_default_validators(self):
        """Register default field validators"""
        try:
            # Agent ID validator
            def validate_agent_id(value):
                return isinstance(value, str) and len(value) > 0 and value.replace('_', '').isalnum()
                
            self.field_validators["agent_id"] = validate_agent_id
            
            # Log level validator
            def validate_log_level(value):
                return isinstance(value, str) and value.upper() in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
                
            self.field_validators["log_level"] = validate_log_level
            
            # Timeout validator
            def validate_timeout(value):
                return isinstance(value, (int, float)) and value > 0
                
            self.field_validators["timeout"] = validate_timeout
            
            # Email validator
            def validate_email(value):
                if not isinstance(value, str):
                    return False
                import re
                pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                return bool(re.match(pattern, value))
                
            self.field_validators["email"] = validate_email
            
        except Exception as e:
            self.logger.error(f"Error registering default validators: {e}")

class ConfigLoader:
    """Safe configuration loading with validation"""
    
    def __init__(self, validator: ConfigValidator = None):
        self.logger = logging.getLogger("config_loader")
        self.validator = validator or ConfigValidator()
        self.loaded_configs = {}
        
    def load_config_file(self, file_path: str, schema: Dict[str, Any] = None) -> tuple[bool, Dict[str, Any], List[str]]:
        """Load and validate configuration file"""
        try:
            if not os.path.exists(file_path):
                return False, {}, [f"Configuration file not found: {file_path}"]
                
            # Load raw config
            with open(file_path, 'r') as f:
                raw_config = f.read()
                
            # Parse JSON
            try:
                config = json.loads(raw_config)
            except json.JSONDecodeError as e:
                return False, {}, [f"Invalid JSON in {file_path}: {e}"]
                
            # Validate configuration
            validation_result = self.validator.validate_config(config, schema)
            
            if validation_result.is_valid:
                self.loaded_configs[file_path] = config
                return True, config, []
            else:
                return False, config, validation_result.errors
                
        except Exception as e:
            self.logger.error(f"Error loading config file {file_path}: {e}")
            return False, {}, [str(e)]
            
    def load_config_env(self, prefix: str = "VH_") -> Dict[str, Any]:
        """Load configuration from environment variables"""
        try:
            config = {}
            
            for key, value in os.environ.items():
                if key.startswith(prefix):
                    config_key = key[len(prefix):].lower()
                    
                    # Try to parse as JSON first
                    try:
                        config[config_key] = json.loads(value)
                    except json.JSONDecodeError:
                        # Try to parse as boolean
                        if value.lower() in ['true', 'false']:
                            config[config_key] = value.lower() == 'true'
                        # Try to parse as number
                        elif value.isdigit():
                            config[config_key] = int(value)
                        # Try to parse as float
                        elif '.' in value and value.replace('.', '').isdigit():
                            config[config_key] = float(value)
                        # Keep as string
                        else:
                            config[config_key] = value
                            
            return config
            
        except Exception as e:
            self.logger.error(f"Error loading config from environment: {e}")
            return {}
            
    def merge_configs(self, base_config: Dict[str, Any], override_config: Dict[str, Any]) -> Dict[str, Any]:
        """Merge configurations with validation"""
        try:
            merged = base_config.copy()
            
            for key, value in override_config.items():
                # Type-aware merging
                if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                    merged[key] = {**merged[key], **value}
                else:
                    merged[key] = value
                    
            return merged
            
        except Exception as e:
            self.logger.error(f"Error merging configs: {e}")
            return base_config
            
    def get_config_value(self, config: Dict[str, Any], key_path: str, default: Any = None) -> Any:
        """Get nested configuration value safely"""
        try:
            keys = key_path.split('.')
            current = config
            
            for key in keys:
                if isinstance(current, dict) and key in current:
                    current = current[key]
                else:
                    return default
                    
            return current
            
        except Exception as e:
            self.logger.error(f"Error getting config value {key_path}: {e}")
            return default
            
    def set_config_value(self, config: Dict[str, Any], key_path: str, value: Any) -> bool:
        """Set nested configuration value safely"""
        try:
            keys = key_path.split('.')
            current = config
            
            for key in keys[:-1]:
                if key not in current:
                    current[key] = {}
                current = current[key]
                
            current[keys[-1]] = value
            return True
            
        except Exception as e:
            self.logger.error(f"Error setting config value {key_path}: {e}")
            return False

class ConfigMigration:
    """Handle configuration migrations"""
    
    def __init__(self):
        self.logger = logging.getLogger("config_migration")
        self.migrations = {}
        
    def register_migration(self, version: str, migration_func: Callable):
        """Register configuration migration"""
        try:
            self.migrations[version] = migration_func
            self.logger.info(f"Registered migration for version {version}")
            
        except Exception as e:
            self.logger.error(f"Error registering migration: {e}")
            
    def migrate_config(self, config: Dict[str, Any], from_version: str, to_version: str) -> tuple[bool, Dict[str, Any], List[str]]:
        """Migrate configuration between versions"""
        try:
            current_config = config.copy()
            errors = []
            
            # Apply migrations in order
            versions = sorted(self.migrations.keys())
            
            for version in versions:
                if from_version < version <= to_version:
                    try:
                        current_config, migration_errors = self.migrations[version](current_config)
                        errors.extend(migration_errors)
                    except Exception as e:
                        errors.append(f"Migration {version} failed: {e}")
                        
            return len(errors) == 0, current_config, errors
            
        except Exception as e:
            self.logger.error(f"Error migrating config: {e}")
            return False, config, [str(e)]
