-- Create database and user
CREATE DATABASE IF NOT EXISTS groceryshopperai CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
-- CREATE USER IF NOT EXISTS 'chatuser'@'localhost' IDENTIFIED BY 'chatpass';
-- GRANT ALL PRIVILEGES ON groceryshopperai.* TO 'chatuser'@'localhost';
CREATE USER IF NOT EXISTS 'chatuser'@'%' IDENTIFIED BY 'Chatpass123!';
GRANT ALL PRIVILEGES ON groceryshopperai.* TO 'chatuser'@'%';
FLUSH PRIVILEGES;

USE groceryshopperai;

-- Users table
CREATE TABLE IF NOT EXISTS users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  username VARCHAR(50) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  preferred_llm_model VARCHAR(50) DEFAULT 'openai' COMMENT 'User preferred LLM model: tinyllama, openai, or gemini',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='User accounts table';

-- Rooms table
CREATE TABLE IF NOT EXISTS rooms (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(100) NOT NULL UNIQUE,
  owner_id INT NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_room_owner FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Chat rooms table';

-- Room members table
CREATE TABLE IF NOT EXISTS room_members (
  id INT AUTO_INCREMENT PRIMARY KEY,
  room_id INT NOT NULL,
  user_id INT NOT NULL,
  joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY unique_room_member (room_id, user_id),
  CONSTRAINT fk_member_room FOREIGN KEY (room_id) REFERENCES rooms(id) ON DELETE CASCADE,
  CONSTRAINT fk_member_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Room membership associations';

-- Messages table
CREATE TABLE IF NOT EXISTS messages (
  id INT AUTO_INCREMENT PRIMARY KEY,
  room_id INT NOT NULL,
  user_id INT NULL,
  content TEXT NOT NULL,
  is_bot BOOLEAN DEFAULT FALSE COMMENT 'TRUE if message is from LLM bot, FALSE if from user',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_message_room FOREIGN KEY (room_id) REFERENCES rooms(id) ON DELETE CASCADE,
  CONSTRAINT fk_message_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Chat messages table';

-- Create indexes for better query performance
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_messages_room_id ON messages(room_id);
CREATE INDEX idx_messages_user_id ON messages(user_id);
CREATE INDEX idx_messages_created_at ON messages(created_at);
CREATE INDEX idx_room_members_room_id ON room_members(room_id);
CREATE INDEX idx_room_members_user_id ON room_members(user_id);
CREATE INDEX idx_rooms_owner_id ON rooms(owner_id);

-- Insert sample data for testing (optional)
-- INSERT INTO users (username, password_hash, preferred_llm_model) VALUES
-- ('admin', '$2b$12$...', 'openai');
-- INSERT INTO rooms (name, owner_id) VALUES
-- ('General', 1),
-- ('Announcements', 1);

CREATE TABLE IF NOT EXISTS inventory (
  product_id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,  -- restaurant/user that owns this product
  product_name VARCHAR(255) NOT NULL,
  stock INT NOT NULL DEFAULT 0,
  safety_stock_level INT NOT NULL DEFAULT 0,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_inventory_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  UNIQUE KEY uniq_user_product (user_id, product_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Per-user/restaurant inventory items';

-- Convert from load_groceries.py
CREATE TABLE IF NOT EXISTS grocery_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    sub_category VARCHAR(120) NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    rating_value FLOAT NULL,
    rating_count INT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_title (title),
    INDEX idx_sub_category (sub_category)
);

-- ===========================================
-- Migration: Add deleted_at to room_members
-- ===========================================
ALTER TABLE room_members
    ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP NULL;

CREATE INDEX IF NOT EXISTS idx_room_members_deleted_at 
    ON room_members (room_id, deleted_at);
