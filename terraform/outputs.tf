output "flag_ids" {
  description = "Created flag IDs"
  value = {
    SAMPLE_API_URL     = launchdarkly_feature_flag.sample_api_url.id
    SAMPLE_SERVICE_URL = launchdarkly_feature_flag.sample_service_url.id
    SAMPLE_APP_URL     = launchdarkly_feature_flag.sample_app_url.id
  }
}


