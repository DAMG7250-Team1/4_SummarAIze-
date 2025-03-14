from flask import Flask, jsonify
import os

app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({"message": "API Keys Deployment Demo"})

@app.route('/api-keys')
def api_keys():
    # Get environment variables and mask them for security
    api_keys = {
        "OPENAI_API_KEY": mask_key(os.environ.get("OPENAI_API_KEY", "")),
        "GOOGLE_API_KEY": mask_key(os.environ.get("GOOGLE_API_KEY", "")),
        "DEEPSEEK_API_KEY": mask_key(os.environ.get("DEEPSEEK_API_KEY", "")),
        "GROK_API_KEY": mask_key(os.environ.get("GROK_API_KEY", "")),
        "ANTHROPIC_API_KEY": mask_key(os.environ.get("ANTHROPIC_API_KEY", "")),
        "DEFAULT_MODEL": os.environ.get("DEFAULT_MODEL", "")
    }
    
    # Also show Redis configuration (masked)
    redis_config = {
        "REDIS_HOST": os.environ.get("REDIS_HOST", ""),
        "REDIS_PORT": os.environ.get("REDIS_PORT", ""),
        "REDIS_PASSWORD": mask_key(os.environ.get("REDIS_PASSWORD", "")),
        "REDIS_SSL": os.environ.get("REDIS_SSL", "")
    }
    
    return jsonify({
        "api_keys": api_keys,
        "redis_config": redis_config,
        "environment": "Google Cloud Run"
    })

def mask_key(key):
    """Mask API keys for security"""
    if not key:
        return ""
    if len(key) <= 8:
        return "****"
    return key[:4] + "****" + key[-4:]

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port, debug=False) 