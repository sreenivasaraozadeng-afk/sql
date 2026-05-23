SET NAMES utf8mb4;

CREATE DATABASE IF NOT EXISTS SeafarerDB
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE SeafarerDB;

CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '用户编号',
    username VARCHAR(50) NOT NULL COMMENT '登录账号',
    password_hash VARCHAR(255) NOT NULL COMMENT '登录密码哈希',
    role VARCHAR(20) NOT NULL COMMENT '系统角色',
    display_name VARCHAR(50) NOT NULL COMMENT '显示名称',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY uq_users_username (username),
    CONSTRAINT ck_users_role CHECK (role IN ('seafarer', 'manager', 'cert_admin', 'shipowner', 'admin'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS crews (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '船员编号',
    user_id INT NOT NULL COMMENT '关联登录用户',
    name VARCHAR(50) NOT NULL COMMENT '姓名',
    gender VARCHAR(10) NOT NULL DEFAULT '男' COMMENT '性别',
    id_card VARCHAR(18) NOT NULL COMMENT '身份证号',
    phone VARCHAR(20) COMMENT '联系电话',
    position VARCHAR(50) NOT NULL COMMENT '适任岗位',
    status VARCHAR(20) NOT NULL DEFAULT 'available' COMMENT '船员状态',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY uq_crews_user_id (user_id),
    UNIQUE KEY uq_crews_id_card (id_card),
    INDEX idx_crews_status (status),
    INDEX idx_crews_position (position),
    CONSTRAINT fk_crews_user FOREIGN KEY (user_id) REFERENCES users(id),
    CONSTRAINT ck_crews_gender CHECK (gender IN ('男', '女')),
    CONSTRAINT ck_crews_status CHECK (status IN ('available', 'pending', 'at_sea', 'inactive'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS certificates (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '证书编号',
    crew_id INT NOT NULL COMMENT '关联船员',
    certificate_type VARCHAR(50) NOT NULL COMMENT '证书类型',
    certificate_no VARCHAR(80) NOT NULL COMMENT '证书号码',
    issued_at DATE NOT NULL COMMENT '签发日期',
    expires_at DATE NOT NULL COMMENT '到期日期',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY uq_certificates_certificate_no (certificate_no),
    INDEX idx_certificates_crew_id (crew_id),
    INDEX idx_certificates_type (certificate_type),
    INDEX idx_certificates_expires_at (expires_at),
    CONSTRAINT fk_certificates_crew FOREIGN KEY (crew_id) REFERENCES crews(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS job_demands (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '岗位需求编号',
    owner_user_id INT NOT NULL COMMENT '发布船东用户',
    title VARCHAR(100) NOT NULL COMMENT '岗位标题',
    ship_name VARCHAR(100) NOT NULL COMMENT '船名',
    route VARCHAR(100) NOT NULL COMMENT '航线',
    required_position VARCHAR(50) NOT NULL COMMENT '所需岗位',
    headcount INT NOT NULL DEFAULT 1 COMMENT '招聘人数',
    onboard_at DATETIME NOT NULL COMMENT '预计上船时间',
    status VARCHAR(20) NOT NULL DEFAULT 'open' COMMENT '岗位状态',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_job_demands_owner_user_id (owner_user_id),
    INDEX idx_job_demands_status (status),
    CONSTRAINT fk_job_demands_owner FOREIGN KEY (owner_user_id) REFERENCES users(id),
    CONSTRAINT ck_job_demands_status CHECK (status IN ('open', 'matched', 'closed'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS job_required_certificates (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '岗位所需证书编号',
    job_id INT NOT NULL COMMENT '关联岗位需求',
    certificate_type VARCHAR(50) NOT NULL COMMENT '证书类型',
    UNIQUE KEY uq_job_required_certificate (job_id, certificate_type),
    INDEX idx_job_required_certificates_job_id (job_id),
    CONSTRAINT fk_job_required_certificates_job FOREIGN KEY (job_id)
        REFERENCES job_demands(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS dispatches (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '派遣编号',
    job_id INT NOT NULL COMMENT '关联岗位需求',
    crew_id INT NOT NULL COMMENT '关联船员',
    status VARCHAR(20) NOT NULL DEFAULT 'pending_owner' COMMENT '派遣状态',
    created_by_user_id INT NOT NULL COMMENT '发起人',
    confirmed_by_user_id INT DEFAULT NULL COMMENT '确认船东',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_dispatches_job_id (job_id),
    INDEX idx_dispatches_crew_id (crew_id),
    INDEX idx_dispatches_status (status),
    CONSTRAINT fk_dispatches_job FOREIGN KEY (job_id) REFERENCES job_demands(id),
    CONSTRAINT fk_dispatches_crew FOREIGN KEY (crew_id) REFERENCES crews(id),
    CONSTRAINT fk_dispatches_created_by FOREIGN KEY (created_by_user_id) REFERENCES users(id),
    CONSTRAINT fk_dispatches_confirmed_by FOREIGN KEY (confirmed_by_user_id) REFERENCES users(id),
    CONSTRAINT ck_dispatches_status CHECK (
        status IN ('pending_owner', 'confirmed', 'onboard', 'offboard', 'cancelled')
    )
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS voyage_records (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '海历编号',
    dispatch_id INT NOT NULL COMMENT '关联派遣',
    crew_id INT NOT NULL COMMENT '关联船员',
    job_id INT NOT NULL COMMENT '关联岗位',
    ship_name VARCHAR(100) NOT NULL COMMENT '船名',
    route VARCHAR(100) NOT NULL COMMENT '航线',
    position VARCHAR(50) NOT NULL COMMENT '岗位',
    onboard_at DATETIME NOT NULL COMMENT '上船时间',
    offboard_at DATETIME DEFAULT NULL COMMENT '下船时间',
    status VARCHAR(20) NOT NULL DEFAULT 'onboard' COMMENT '海历状态',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY uq_voyage_records_dispatch_id (dispatch_id),
    INDEX idx_voyage_records_crew_id (crew_id),
    INDEX idx_voyage_records_status (status),
    CONSTRAINT fk_voyage_records_dispatch FOREIGN KEY (dispatch_id) REFERENCES dispatches(id),
    CONSTRAINT fk_voyage_records_crew FOREIGN KEY (crew_id) REFERENCES crews(id),
    CONSTRAINT fk_voyage_records_job FOREIGN KEY (job_id) REFERENCES job_demands(id),
    CONSTRAINT ck_voyage_records_status CHECK (status IN ('onboard', 'offboard', 'cancelled'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO users (username, password_hash, role, display_name) VALUES
(
    'admin',
    'pbkdf2_sha256$120000$admin-seed$26b950a60b7703635f187e9d39d6ed5a07eec11803a488eccaff376e6d23cb6c',
    'admin',
    '系统管理员'
),
(
    'manager',
    'pbkdf2_sha256$120000$manager-seed$68853fd1d1bb45ec57f40cfa6bd3928535cb85d3e810d72f6faeddd936847cc4',
    'manager',
    '业务经理'
),
(
    'cert_admin',
    'pbkdf2_sha256$120000$cert_admin-seed$20648f9c90bdf1701583b33fb902ddc52ead8f31c1d30753d86d22c77bd3b40e',
    'cert_admin',
    '证书管理员'
),
(
    'owner',
    'pbkdf2_sha256$120000$owner-seed$aca757b9154662dc91b1594da1dccb6d0c1cfd406844b4a4656ff3c3d386a277',
    'shipowner',
    '船东甲'
),
(
    'other_owner',
    'pbkdf2_sha256$120000$other_owner-seed$45edeae371a9e7ea9f7b4b1431f13c28696f973907170a17b2ca3dc8893efe94',
    'shipowner',
    '船东乙'
),
(
    'crew01',
    'pbkdf2_sha256$120000$crew01-seed$7e760d85b648f173cee5c7867101a6ee683bc8691562f6bc901d4cbfb24d6de1',
    'seafarer',
    '张三'
);

INSERT INTO crews (user_id, name, gender, id_card, phone, position, status) VALUES
(
    (SELECT id FROM users WHERE username = 'crew01'),
    '张三',
    '男',
    '110101199001011234',
    '13800000001',
    '水手',
    'available'
);

INSERT INTO certificates (crew_id, certificate_type, certificate_no, issued_at, expires_at) VALUES
(
    (SELECT id FROM crews WHERE id_card = '110101199001011234'),
    'STCW',
    'STCW-DEMO-001',
    '2026-01-01',
    '2027-01-01'
);

INSERT INTO job_demands (
    owner_user_id,
    title,
    ship_name,
    route,
    required_position,
    headcount,
    onboard_at,
    status
) VALUES
(
    (SELECT id FROM users WHERE username = 'owner'),
    '远洋水手',
    '东方一号',
    '青岛-新加坡',
    '水手',
    1,
    '2026-06-01 08:00:00',
    'open'
);

INSERT INTO job_required_certificates (job_id, certificate_type) VALUES
(
    (SELECT id FROM job_demands WHERE title = '远洋水手' LIMIT 1),
    'STCW'
);
