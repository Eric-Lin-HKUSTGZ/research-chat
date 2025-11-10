# Research Chat 数据库初始化脚本
# 作为 digital_twin_academic 系统的子模块
# 所有表名添加 research_chat_ 前缀以区分

-- 使用与 digital_twin_academic 相同的数据库
USE sci_agent_academic;

-- Users (account)
CREATE TABLE IF NOT EXISTS users (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
  email VARCHAR(128) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  username VARCHAR(255) NULL,
  identity_tag ENUM('student','researcher','pioneer') COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_users_email (email)
) ENGINE=InnoDB CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 会话表
CREATE TABLE IF NOT EXISTS research_chat_sessions (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
  page_session_id VARCHAR(128) NOT NULL,
  session_name VARCHAR(255) NULL,
  user_id BIGINT UNSIGNED NOT NULL,
  email VARCHAR(128) NOT NULL,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_rc_page_session (page_session_id),
  INDEX idx_rc_owner (user_id),
  INDEX idx_rc_email (email),
  CONSTRAINT fk_rc_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE ON UPDATE RESTRICT
) ENGINE=InnoDB CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 存储用户输入和大模型最终输出
CREATE TABLE IF NOT EXISTS research_chat_messages (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
  session_id BIGINT UNSIGNED NOT NULL,
  user_id BIGINT UNSIGNED NOT NULL,
  email VARCHAR(128) NOT NULL,
  content LONGTEXT NOT NULL,
  result_papers JSON NULL,
  extra_info JSON NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_rc_session (session_id),
  INDEX idx_rc_user (user_id),
  INDEX idx_rc_email (email),
  CONSTRAINT fk_rc_session FOREIGN KEY (session_id) REFERENCES research_chat_sessions(id) ON DELETE CASCADE ON UPDATE RESTRICT
) ENGINE=InnoDB CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 额外的API专用表 - 用于存储进程信息
CREATE TABLE IF NOT EXISTS research_chat_process_infos (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
  session_id BIGINT UNSIGNED NOT NULL,
  message_id BIGINT UNSIGNED NOT NULL,
  user_id BIGINT UNSIGNED NOT NULL,
  email VARCHAR(128) NOT NULL,
  process_info JSON NULL,
  extra_info JSON NULL,
  creation_status ENUM('pending','creating','created','failed') NOT NULL DEFAULT 'pending',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_rc_message (message_id),
  INDEX idx_rc_session (session_id),
  INDEX idx_rc_user (user_id),
  INDEX idx_rc_email (email),
  CONSTRAINT fk_rc_message FOREIGN KEY (message_id) REFERENCES research_chat_messages(id) ON DELETE CASCADE ON UPDATE RESTRICT
) ENGINE=InnoDB CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;