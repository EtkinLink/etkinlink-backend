"""
Configuration settings for the application.
"""
import os


class Config:
    """Base configuration class."""
    
    # Secret key for JWT and Flask
    SECRET_KEY = os.getenv('SECRET_KEY')
    
    # Database
    DATABASE_URL = os.getenv("DATABASE_URL")

    
    # Application
    PORT = int(os.getenv("PORT", 8000))
    
    # Frontend URL for password reset emails
    FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:3000')


class DevelopmentConfig(Config):
    """Development environment configuration."""
    DEBUG = True


class ProductionConfig(Config):
    """Production environment configuration."""
    DEBUG = False


# Configuration dictionary
config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}


def get_config():
    """Get configuration based on environment."""
    env = os.getenv('FLASK_ENV', 'development')
    return config_by_name.get(env, DevelopmentConfig)
