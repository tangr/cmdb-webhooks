CREATE TABLE IF NOT EXISTS `jms_reqlog` (
  `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT,
  `jmshost` varchar(255) NOT NULL,
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
