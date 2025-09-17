terraform {
  required_version = ">= 1.4.0"
  required_providers {
    launchdarkly = {
      source  = "launchdarkly/launchdarkly"
      version = "~> 2.0"
    }
  }
}

provider "launchdarkly" {
  access_token = var.launchdarkly_access_token
}

# SAMPLE_API_URL
resource "launchdarkly_feature_flag" "sample_api_url" {
  project_key    = var.project_key
  key            = "SAMPLE_API_URL"
  name           = "SAMPLE_API_URL"
  description    = "API endpoint with v2, v1, and fallback variations"
  variation_type = "string"

  variations {
    value       = "https://api-v2.example.com"
    name        = "API v2"
    description = "API v2 endpoint"
  }

  variations {
    value       = "https://api-v1.example.com"
    name        = "API v1"
    description = "API v1 endpoint"
  }

  variations {
    value       = "https://api-default.example.com"
    name        = "fallback API"
    description = "Fallback API endpoint"
  }

  # Use v2 when on; fallback when off
  defaults {
    on_variation  = 0
    off_variation = 2
  }

  tags = ["managed-by-terraform", "ld-env-sync-demo"]
}

resource "launchdarkly_feature_flag_environment" "sample_api_url_env" {
  flag_id = launchdarkly_feature_flag.sample_api_url.id
  env_key = var.environment_key

  on = true

  fallthrough {
    variation = 0 # API v2
  }

  off_variation = 2 # fallback API
}

# SAMPLE_SERVICE_URL
resource "launchdarkly_feature_flag" "sample_service_url" {
  project_key    = var.project_key
  key            = "SAMPLE_SERVICE_URL"
  name           = "SAMPLE_SERVICE_URL"
  description    = "Service endpoint with v2, v1, and base variations"
  variation_type = "string"

  variations {
    value       = "https://app-api-v2.example.com"
    name        = "SAMPLE_APP_URL v2"
    description = "Service v2 endpoint"
  }

  variations {
    value       = "https://app-api-v1.example.com"
    name        = "SAMPLE_APP_URL v1"
    description = "Service v1 endpoint"
  }

  variations {
    value       = "https://app-api.example.com"
    name        = "SAMPLE_APP_URL Base"
    description = "Service base endpoint"
  }

  defaults {
    on_variation  = 0
    off_variation = 2
  }

  tags = ["managed-by-terraform", "ld-env-sync-demo"]
}

resource "launchdarkly_feature_flag_environment" "sample_service_url_env" {
  flag_id = launchdarkly_feature_flag.sample_service_url.id
  env_key = var.environment_key

  on = true

  fallthrough {
    variation = 0 # v2
  }

  off_variation = 2 # base
}

# SAMPLE_APP_URL
resource "launchdarkly_feature_flag" "sample_app_url" {
  project_key    = var.project_key
  key            = "SAMPLE_APP_URL"
  name           = "SAMPLE_APP_URL"
  description    = "App endpoint with v2, v1, and base variations"
  variation_type = "string"

  variations {
    value       = "https://app-api-v2.example.com"
    name        = "SAMPLE_APP_URL v2"
    description = "App v2 endpoint"
  }

  variations {
    value       = "https://app-api-v1.example.com"
    name        = "SAMPLE_APP_URL v1"
    description = "App v1 endpoint"
  }

  variations {
    value       = "https://app-api.example.com"
    name        = "SAMPLE_APP_URL Base"
    description = "App base endpoint"
  }

  defaults {
    on_variation  = 0
    off_variation = 2
  }

  tags = ["managed-by-terraform", "ld-env-sync-demo"]
}

resource "launchdarkly_feature_flag_environment" "sample_app_url_env" {
  flag_id = launchdarkly_feature_flag.sample_app_url.id
  env_key = var.environment_key

  on = true

  fallthrough {
    variation = 0 # v2
  }

  off_variation = 2 # base
}

 


