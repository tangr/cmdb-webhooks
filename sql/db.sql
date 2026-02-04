CREATE TABLE IF NOT EXISTS `cmdb_reqlog` (
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

CREATE TABLE IF NOT EXISTS `feishu_reqlog` (
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

CREATE TABLE IF NOT EXISTS `gitlab_reqlog` (
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
