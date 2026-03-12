CREATE TABLE IF NOT EXISTS `cmdb_trigger_reqlog` (
  `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT,
  `host` varchar(255) NOT NULL,
  `method` varchar(255) NOT NULL,
  `path` varchar(255) NOT NULL,
  `query` varchar(255) NOT NULL,
  `headers` JSON NOT NULL,
  `body` JSON NOT NULL,
  `author` varchar(255) NOT NULL,
  `clientip` varchar(255) NOT NULL,
  `status` int(11) UNSIGNED NOT NULL,
  `output` longtext DEFAULT NULL,
  `created_at` bigint(10) UNSIGNED NOT NULL,
  `updated_at` bigint(10) UNSIGNED NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=10000 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `feishu_bot_reqlog` (
  `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT,
  `webhook_id` varchar(255) NOT NULL,
  `method` varchar(255) NOT NULL,
  `path` varchar(255) NOT NULL,
  `query` varchar(255) NOT NULL,
  `headers` JSON NOT NULL,
  `body` JSON NOT NULL,
  `clientip` varchar(255) NOT NULL,
  `status` int(11) UNSIGNED NOT NULL,
  `response_headers` JSON DEFAULT NULL,
  `response_body` JSON DEFAULT NULL,
  `error_message` longtext DEFAULT NULL,
  `created_at` bigint(10) UNSIGNED NOT NULL,
  `updated_at` bigint(10) UNSIGNED NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=10000 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `gitlab_hook_reqlog` (
  `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT,
  `event_type` varchar(50) NOT NULL COMMENT 'Event type: push, tag_push, merge_request',
  `project_path` varchar(255) NOT NULL COMMENT 'GitLab project path with namespace',
  `method` varchar(10) NOT NULL,
  `path` varchar(255) NOT NULL,
  `headers` JSON NOT NULL,
  `body` JSON NOT NULL,
  `clientip` varchar(45) NOT NULL,
  `status` int(11) UNSIGNED NOT NULL,
  `jenkins_job` varchar(255) DEFAULT NULL COMMENT 'Target Jenkins job name',
  `jenkins_response` JSON DEFAULT NULL COMMENT 'Response from Jenkins',
  `error_message` longtext DEFAULT NULL,
  `created_at` bigint(10) UNSIGNED NOT NULL,
  `updated_at` bigint(10) UNSIGNED NOT NULL,
  PRIMARY KEY (`id`),
  INDEX `idx_event_type` (`event_type`),
  INDEX `idx_project_path` (`project_path`),
  INDEX `idx_created_at` (`created_at`)
) ENGINE=InnoDB AUTO_INCREMENT=10000 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `amis_jenkins_reqlog` (
  `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT,
  `form_id` varchar(100) NOT NULL COMMENT 'Amis form identifier',
  `form_title` varchar(255) NOT NULL COMMENT 'Form display title',
  `trigger_type` varchar(50) NOT NULL COMMENT 'Trigger type: generic_webhook or remote_api',
  `jenkins_job` varchar(255) NOT NULL COMMENT 'Target Jenkins job name',
  `request_params` JSON NOT NULL COMMENT 'User submitted form parameters',
  `clientip` varchar(45) NOT NULL,
  `username` varchar(255) NOT NULL COMMENT 'Submitting user',
  `status` int(11) UNSIGNED NOT NULL,
  `jenkins_response` JSON DEFAULT NULL COMMENT 'Response from Jenkins',
  `error_message` longtext DEFAULT NULL,
  `created_at` bigint(10) UNSIGNED NOT NULL,
  `updated_at` bigint(10) UNSIGNED NOT NULL,
  PRIMARY KEY (`id`),
  INDEX `idx_form_id` (`form_id`),
  INDEX `idx_username` (`username`),
  INDEX `idx_created_at` (`created_at`)
) ENGINE=InnoDB AUTO_INCREMENT=10000 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `feishu_approval_reqlog` (
  `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT,
  `app_name` varchar(100) NOT NULL COMMENT 'Feishu app name from config',
  `approval_code` varchar(100) NOT NULL COMMENT 'Feishu approval definition code',
  `feishu_instance_code` varchar(100) DEFAULT NULL COMMENT 'Feishu approval instance code',
  `feishu_user_id` varchar(100) NOT NULL COMMENT 'Feishu user ID (short format)',
  `status` varchar(50) NOT NULL DEFAULT 'pending' COMMENT 'Approval status: pending, approved, rejected, canceled, error',
  `form_data` JSON NOT NULL COMMENT 'Form data submitted with approval',
  `username` varchar(255) NOT NULL COMMENT 'Submitting user from session',
  `clientip` varchar(45) NOT NULL,
  `feishu_response` JSON DEFAULT NULL COMMENT 'Response from Feishu API',
  `error_message` longtext DEFAULT NULL,
  `created_at` bigint(10) UNSIGNED NOT NULL,
  `updated_at` bigint(10) UNSIGNED NOT NULL,
  PRIMARY KEY (`id`),
  INDEX `idx_app_name` (`app_name`),
  INDEX `idx_feishu_instance_code` (`feishu_instance_code`),
  INDEX `idx_username` (`username`),
  INDEX `idx_status` (`status`),
  INDEX `idx_created_at` (`created_at`)
) ENGINE=InnoDB AUTO_INCREMENT=10000 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
