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

CREATE TABLE IF NOT EXISTS ship_companies (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '航运公司编号',
    name VARCHAR(100) NOT NULL COMMENT '公司名称',
    owner_user_id INT DEFAULT NULL COMMENT '关联船东用户',
    contact_name VARCHAR(50) DEFAULT NULL COMMENT '联系人',
    phone VARCHAR(20) DEFAULT NULL COMMENT '联系电话',
    address VARCHAR(200) DEFAULT NULL COMMENT '公司地址',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY uq_ship_companies_name (name),
    INDEX idx_ship_companies_owner_user_id (owner_user_id),
    CONSTRAINT fk_ship_companies_owner FOREIGN KEY (owner_user_id) REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS ships (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '船舶编号',
    company_id INT NOT NULL COMMENT '所属航运公司',
    name VARCHAR(100) NOT NULL COMMENT '船名',
    ship_type VARCHAR(50) NOT NULL DEFAULT '散货船' COMMENT '船舶类型',
    tonnage INT DEFAULT NULL COMMENT '吨位',
    capacity INT DEFAULT NULL COMMENT '核定船员人数',
    status VARCHAR(20) NOT NULL DEFAULT 'active' COMMENT '船舶状态',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY uq_ships_name (name),
    INDEX idx_ships_company_id (company_id),
    INDEX idx_ships_status (status),
    CONSTRAINT fk_ships_company FOREIGN KEY (company_id) REFERENCES ship_companies(id),
    CONSTRAINT ck_ships_status CHECK (status IN ('active', 'maintenance', 'inactive'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS ports (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '港口编号',
    name VARCHAR(100) NOT NULL COMMENT '港口名称',
    country VARCHAR(50) NOT NULL DEFAULT '中国' COMMENT '国家',
    city VARCHAR(50) DEFAULT NULL COMMENT '城市',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY uq_ports_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS routes (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '航线编号',
    route_name VARCHAR(120) NOT NULL COMMENT '航线名称',
    departure_port_id INT NOT NULL COMMENT '出发港',
    destination_port_id INT NOT NULL COMMENT '目的港',
    distance_nm INT DEFAULT NULL COMMENT '航程海里',
    estimated_days INT DEFAULT NULL COMMENT '预计航行天数',
    status VARCHAR(20) NOT NULL DEFAULT 'active' COMMENT '航线状态',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY uq_routes_path_name (departure_port_id, destination_port_id, route_name),
    INDEX idx_routes_departure_port_id (departure_port_id),
    INDEX idx_routes_destination_port_id (destination_port_id),
    INDEX idx_routes_status (status),
    CONSTRAINT fk_routes_departure_port FOREIGN KEY (departure_port_id) REFERENCES ports(id),
    CONSTRAINT fk_routes_destination_port FOREIGN KEY (destination_port_id) REFERENCES ports(id),
    CONSTRAINT ck_routes_status CHECK (status IN ('active', 'inactive')),
    CONSTRAINT ck_routes_different_ports CHECK (departure_port_id <> destination_port_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS positions (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '岗位编号',
    name VARCHAR(50) NOT NULL COMMENT '岗位名称',
    level VARCHAR(30) DEFAULT NULL COMMENT '岗位等级',
    base_salary INT DEFAULT NULL COMMENT '参考薪资',
    description VARCHAR(200) DEFAULT NULL COMMENT '岗位说明',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY uq_positions_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS certificate_types (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '证书类型编号',
    name VARCHAR(50) NOT NULL COMMENT '证书类型名称',
    validity_months INT DEFAULT NULL COMMENT '默认有效月数',
    is_required BOOLEAN NOT NULL DEFAULT TRUE COMMENT '是否常用必备证书',
    description VARCHAR(200) DEFAULT NULL COMMENT '证书说明',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY uq_certificate_types_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS crews (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '船员编号',
    user_id INT NOT NULL COMMENT '关联登录用户',
    position_id INT DEFAULT NULL COMMENT '关联岗位',
    name VARCHAR(50) NOT NULL COMMENT '姓名',
    gender VARCHAR(10) NOT NULL DEFAULT '男' COMMENT '性别',
    id_card VARCHAR(18) NOT NULL COMMENT '身份证号',
    phone VARCHAR(20) DEFAULT NULL COMMENT '联系电话',
    position VARCHAR(50) NOT NULL COMMENT '适任岗位名称',
    status VARCHAR(20) NOT NULL DEFAULT 'available' COMMENT '船员状态',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY uq_crews_user_id (user_id),
    UNIQUE KEY uq_crews_id_card (id_card),
    INDEX idx_crews_status (status),
    INDEX idx_crews_position (position),
    INDEX idx_crews_position_id (position_id),
    CONSTRAINT fk_crews_user FOREIGN KEY (user_id) REFERENCES users(id),
    CONSTRAINT fk_crews_position FOREIGN KEY (position_id) REFERENCES positions(id),
    CONSTRAINT ck_crews_gender CHECK (gender IN ('男', '女')),
    CONSTRAINT ck_crews_status CHECK (status IN ('available', 'pending', 'at_sea', 'inactive'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS certificates (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '证书编号',
    crew_id INT NOT NULL COMMENT '关联船员',
    certificate_type_id INT DEFAULT NULL COMMENT '关联证书类型',
    certificate_type VARCHAR(50) NOT NULL COMMENT '证书类型名称',
    certificate_no VARCHAR(80) NOT NULL COMMENT '证书号码',
    issued_at DATE NOT NULL COMMENT '签发日期',
    expires_at DATE NOT NULL COMMENT '到期日期',
    review_status VARCHAR(20) NOT NULL DEFAULT 'pending' COMMENT '审核状态',
    reviewed_by_user_id INT DEFAULT NULL COMMENT '审核人',
    reviewed_at DATETIME DEFAULT NULL COMMENT '审核时间',
    review_remark VARCHAR(200) DEFAULT NULL COMMENT '审核备注',
    attachment_url VARCHAR(300) DEFAULT NULL COMMENT '附件地址',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY uq_certificates_certificate_no (certificate_no),
    INDEX idx_certificates_crew_id (crew_id),
    INDEX idx_certificates_type (certificate_type),
    INDEX idx_certificates_certificate_type_id (certificate_type_id),
    INDEX idx_certificates_expires_at (expires_at),
    INDEX idx_certificates_review_status (review_status),
    CONSTRAINT fk_certificates_crew FOREIGN KEY (crew_id) REFERENCES crews(id) ON DELETE CASCADE,
    CONSTRAINT fk_certificates_certificate_type FOREIGN KEY (certificate_type_id) REFERENCES certificate_types(id),
    CONSTRAINT fk_certificates_reviewed_by FOREIGN KEY (reviewed_by_user_id) REFERENCES users(id),
    CONSTRAINT ck_certificates_review_status CHECK (review_status IN ('pending', 'approved', 'rejected'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS certificate_review_records (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '证书审核记录编号',
    certificate_id INT NOT NULL COMMENT '关联证书',
    reviewer_user_id INT NOT NULL COMMENT '审核用户',
    old_status VARCHAR(20) NOT NULL COMMENT '原审核状态',
    new_status VARCHAR(20) NOT NULL COMMENT '新审核状态',
    remark VARCHAR(200) DEFAULT NULL COMMENT '审核说明',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_certificate_review_records_certificate_id (certificate_id),
    INDEX idx_certificate_review_records_reviewer_user_id (reviewer_user_id),
    CONSTRAINT fk_certificate_review_records_certificate FOREIGN KEY (certificate_id)
        REFERENCES certificates(id) ON DELETE CASCADE,
    CONSTRAINT fk_certificate_review_records_reviewer FOREIGN KEY (reviewer_user_id) REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS job_demands (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '岗位需求编号',
    owner_user_id INT NOT NULL COMMENT '发布船东用户',
    ship_id INT DEFAULT NULL COMMENT '关联船舶',
    route_id INT DEFAULT NULL COMMENT '关联航线',
    position_id INT DEFAULT NULL COMMENT '关联岗位',
    title VARCHAR(100) NOT NULL COMMENT '岗位标题',
    ship_name VARCHAR(100) NOT NULL COMMENT '船名',
    route VARCHAR(120) NOT NULL COMMENT '航线',
    required_position VARCHAR(50) NOT NULL COMMENT '所需岗位',
    headcount INT NOT NULL DEFAULT 1 COMMENT '招聘人数',
    onboard_at DATETIME NOT NULL COMMENT '预计上船时间',
    status VARCHAR(20) NOT NULL DEFAULT 'open' COMMENT '岗位状态',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_job_demands_owner_user_id (owner_user_id),
    INDEX idx_job_demands_ship_id (ship_id),
    INDEX idx_job_demands_route_id (route_id),
    INDEX idx_job_demands_position_id (position_id),
    INDEX idx_job_demands_status (status),
    CONSTRAINT fk_job_demands_owner FOREIGN KEY (owner_user_id) REFERENCES users(id),
    CONSTRAINT fk_job_demands_ship FOREIGN KEY (ship_id) REFERENCES ships(id),
    CONSTRAINT fk_job_demands_route FOREIGN KEY (route_id) REFERENCES routes(id),
    CONSTRAINT fk_job_demands_position FOREIGN KEY (position_id) REFERENCES positions(id),
    CONSTRAINT ck_job_demands_status CHECK (status IN ('open', 'matched', 'closed')),
    CONSTRAINT ck_job_demands_headcount CHECK (headcount > 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS job_required_certificates (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '岗位所需证书编号',
    job_id INT NOT NULL COMMENT '关联岗位需求',
    certificate_type_id INT DEFAULT NULL COMMENT '关联证书类型',
    certificate_type VARCHAR(50) NOT NULL COMMENT '证书类型名称',
    UNIQUE KEY uq_job_required_certificate (job_id, certificate_type),
    INDEX idx_job_required_certificates_job_id (job_id),
    INDEX idx_job_required_certificates_certificate_type_id (certificate_type_id),
    CONSTRAINT fk_job_required_certificates_job FOREIGN KEY (job_id)
        REFERENCES job_demands(id) ON DELETE CASCADE,
    CONSTRAINT fk_job_required_certificates_type FOREIGN KEY (certificate_type_id)
        REFERENCES certificate_types(id)
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

CREATE TABLE IF NOT EXISTS dispatch_status_logs (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '派遣状态日志编号',
    dispatch_id INT NOT NULL COMMENT '关联派遣',
    old_status VARCHAR(20) DEFAULT NULL COMMENT '原状态',
    new_status VARCHAR(20) NOT NULL COMMENT '新状态',
    operator_user_id INT DEFAULT NULL COMMENT '操作用户',
    remark VARCHAR(200) DEFAULT NULL COMMENT '状态说明',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_dispatch_status_logs_dispatch_id (dispatch_id),
    INDEX idx_dispatch_status_logs_operator_user_id (operator_user_id),
    CONSTRAINT fk_dispatch_status_logs_dispatch FOREIGN KEY (dispatch_id)
        REFERENCES dispatches(id) ON DELETE CASCADE,
    CONSTRAINT fk_dispatch_status_logs_operator FOREIGN KEY (operator_user_id) REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS voyage_records (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '海历编号',
    dispatch_id INT NOT NULL COMMENT '关联派遣',
    crew_id INT NOT NULL COMMENT '关联船员',
    job_id INT NOT NULL COMMENT '关联岗位',
    ship_name VARCHAR(100) NOT NULL COMMENT '船名',
    route VARCHAR(120) NOT NULL COMMENT '航线',
    position VARCHAR(50) NOT NULL COMMENT '岗位',
    onboard_at DATETIME NOT NULL COMMENT '上船时间',
    offboard_at DATETIME DEFAULT NULL COMMENT '下船时间',
    status VARCHAR(20) NOT NULL DEFAULT 'onboard' COMMENT '海历状态',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY uq_voyage_records_dispatch_id (dispatch_id),
    INDEX idx_voyage_records_crew_id (crew_id),
    INDEX idx_voyage_records_job_id (job_id),
    INDEX idx_voyage_records_status (status),
    CONSTRAINT fk_voyage_records_dispatch FOREIGN KEY (dispatch_id) REFERENCES dispatches(id),
    CONSTRAINT fk_voyage_records_crew FOREIGN KEY (crew_id) REFERENCES crews(id),
    CONSTRAINT fk_voyage_records_job FOREIGN KEY (job_id) REFERENCES job_demands(id),
    CONSTRAINT ck_voyage_records_status CHECK (status IN ('onboard', 'offboard', 'cancelled'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS operation_logs (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '操作日志编号',
    user_id INT DEFAULT NULL COMMENT '操作用户',
    username VARCHAR(50) DEFAULT NULL COMMENT '操作账号',
    action VARCHAR(50) NOT NULL COMMENT '操作类型',
    target_type VARCHAR(50) NOT NULL COMMENT '对象类型',
    target_id INT DEFAULT NULL COMMENT '对象编号',
    detail TEXT DEFAULT NULL COMMENT '操作详情',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_operation_logs_user_id (user_id),
    INDEX idx_operation_logs_action (action),
    INDEX idx_operation_logs_target (target_type, target_id),
    INDEX idx_operation_logs_created_at (created_at),
    CONSTRAINT fk_operation_logs_user FOREIGN KEY (user_id) REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO users (username, password_hash, role, display_name) VALUES
('admin', 'pbkdf2_sha256$120000$admin-seed$26b950a60b7703635f187e9d39d6ed5a07eec11803a488eccaff376e6d23cb6c', 'admin', '系统管理员'),
('manager', 'pbkdf2_sha256$120000$manager-seed$68853fd1d1bb45ec57f40cfa6bd3928535cb85d3e810d72f6faeddd936847cc4', 'manager', '业务经理'),
('cert_admin', 'pbkdf2_sha256$120000$cert_admin-seed$20648f9c90bdf1701583b33fb902ddc52ead8f31c1d30753d86d22c77bd3b40e', 'cert_admin', '证书管理员'),
('owner', 'pbkdf2_sha256$120000$owner-seed$aca757b9154662dc91b1594da1dccb6d0c1cfd406844b4a4656ff3c3d386a277', 'shipowner', '船东甲'),
('other_owner', 'pbkdf2_sha256$120000$other_owner-seed$45edeae371a9e7ea9f7b4b1431f13c28696f973907170a17b2ca3dc8893efe94', 'shipowner', '船东乙'),
('crew01', 'pbkdf2_sha256$120000$crew01-seed$7e760d85b648f173cee5c7867101a6ee683bc8691562f6bc901d4cbfb24d6de1', 'seafarer', '张三'),
('crew02', 'pbkdf2_sha256$120000$crew01-seed$7e760d85b648f173cee5c7867101a6ee683bc8691562f6bc901d4cbfb24d6de1', 'seafarer', '李四'),
('crew03', 'pbkdf2_sha256$120000$crew01-seed$7e760d85b648f173cee5c7867101a6ee683bc8691562f6bc901d4cbfb24d6de1', 'seafarer', '王五'),
('crew04', 'pbkdf2_sha256$120000$crew01-seed$7e760d85b648f173cee5c7867101a6ee683bc8691562f6bc901d4cbfb24d6de1', 'seafarer', '赵六'),
('crew05', 'pbkdf2_sha256$120000$crew01-seed$7e760d85b648f173cee5c7867101a6ee683bc8691562f6bc901d4cbfb24d6de1', 'seafarer', '陈七'),
('crew06', 'pbkdf2_sha256$120000$crew01-seed$7e760d85b648f173cee5c7867101a6ee683bc8691562f6bc901d4cbfb24d6de1', 'seafarer', '周八'),
('crew07', 'pbkdf2_sha256$120000$crew01-seed$7e760d85b648f173cee5c7867101a6ee683bc8691562f6bc901d4cbfb24d6de1', 'seafarer', '吴九'),
('crew08', 'pbkdf2_sha256$120000$crew01-seed$7e760d85b648f173cee5c7867101a6ee683bc8691562f6bc901d4cbfb24d6de1', 'seafarer', '郑十');

INSERT INTO positions (name, level, base_salary, description) VALUES
('船长', '高级船员', 36000, '负责船舶航行和安全管理'),
('轮机长', '高级船员', 34000, '负责机舱设备和动力系统'),
('大副', '高级船员', 26000, '负责甲板部管理和值班'),
('二副', '驾驶部', 20000, '负责航行值班和航海资料'),
('水手', '普通船员', 12000, '负责甲板作业和值班'),
('机工', '普通船员', 12000, '负责机舱日常维护');

INSERT INTO certificate_types (name, validity_months, is_required, description) VALUES
('STCW', 60, TRUE, '国际海员培训、发证和值班标准证书'),
('GMDSS', 60, TRUE, '全球海上遇险与安全系统证书'),
('高级消防', 60, TRUE, '高级消防培训合格证'),
('油化证', 60, TRUE, '油船/化学品船适任证书'),
('健康证', 24, TRUE, '海员健康体检证明');

INSERT INTO ports (name, country, city) VALUES
('上海港', '中国', '上海'),
('青岛港', '中国', '青岛'),
('宁波舟山港', '中国', '宁波'),
('新加坡港', '新加坡', '新加坡'),
('鹿特丹港', '荷兰', '鹿特丹');

INSERT INTO routes (route_name, departure_port_id, destination_port_id, distance_nm, estimated_days) VALUES
('中近洋补给线', (SELECT id FROM ports WHERE name = '上海港'), (SELECT id FROM ports WHERE name = '新加坡港'), 2100, 8),
('远洋集装箱线', (SELECT id FROM ports WHERE name = '青岛港'), (SELECT id FROM ports WHERE name = '鹿特丹港'), 10500, 32),
('东南亚散货线', (SELECT id FROM ports WHERE name = '宁波舟山港'), (SELECT id FROM ports WHERE name = '新加坡港'), 1900, 7),
('欧洲回程线', (SELECT id FROM ports WHERE name = '鹿特丹港'), (SELECT id FROM ports WHERE name = '上海港'), 10800, 34);

INSERT INTO ship_companies (name, owner_user_id, contact_name, phone, address) VALUES
('东方航运', (SELECT id FROM users WHERE username = 'owner'), '船东甲', '13900000001', '上海市浦东新区'),
('北海船务', (SELECT id FROM users WHERE username = 'other_owner'), '船东乙', '13900000002', '青岛市市南区');

INSERT INTO ships (company_id, name, ship_type, tonnage, capacity, status) VALUES
((SELECT id FROM ship_companies WHERE name = '东方航运'), '东方一号', '散货船', 56000, 24, 'active'),
((SELECT id FROM ship_companies WHERE name = '东方航运'), '东方二号', '集装箱船', 72000, 28, 'active'),
((SELECT id FROM ship_companies WHERE name = '北海船务'), '北海远航', '油化船', 48000, 22, 'active'),
((SELECT id FROM ship_companies WHERE name = '北海船务'), '海晟88', '散货船', 51000, 24, 'maintenance');

INSERT INTO crews (user_id, position_id, name, gender, id_card, phone, position, status) VALUES
((SELECT id FROM users WHERE username = 'crew01'), (SELECT id FROM positions WHERE name = '水手'), '张三', '男', '110101199001011234', '13800000001', '水手', 'available'),
((SELECT id FROM users WHERE username = 'crew02'), (SELECT id FROM positions WHERE name = '机工'), '李四', '男', '110101199202022222', '13800000002', '机工', 'at_sea'),
((SELECT id FROM users WHERE username = 'crew03'), (SELECT id FROM positions WHERE name = '船长'), '王五', '男', '110101198803033333', '13800000003', '船长', 'available'),
((SELECT id FROM users WHERE username = 'crew04'), (SELECT id FROM positions WHERE name = '大副'), '赵六', '女', '110101199404044444', '13800000004', '大副', 'available'),
((SELECT id FROM users WHERE username = 'crew05'), (SELECT id FROM positions WHERE name = '二副'), '陈七', '男', '110101199505055555', '13800000005', '二副', 'pending'),
((SELECT id FROM users WHERE username = 'crew06'), (SELECT id FROM positions WHERE name = '轮机长'), '周八', '男', '110101198706066666', '13800000006', '轮机长', 'available'),
((SELECT id FROM users WHERE username = 'crew07'), (SELECT id FROM positions WHERE name = '水手'), '吴九', '男', '110101199707077777', '13800000007', '水手', 'available'),
((SELECT id FROM users WHERE username = 'crew08'), (SELECT id FROM positions WHERE name = '机工'), '郑十', '女', '110101199808088888', '13800000008', '机工', 'available');

INSERT INTO certificates (
    crew_id, certificate_type_id, certificate_type, certificate_no, issued_at, expires_at,
    review_status, reviewed_by_user_id, reviewed_at, review_remark
) VALUES
((SELECT id FROM crews WHERE name = '张三'), (SELECT id FROM certificate_types WHERE name = 'STCW'), 'STCW', 'STCW-ZS-001', '2024-01-01', '2028-01-01', 'approved', (SELECT id FROM users WHERE username = 'cert_admin'), '2026-05-01 09:00:00', '材料完整'),
((SELECT id FROM crews WHERE name = '张三'), (SELECT id FROM certificate_types WHERE name = '健康证'), '健康证', 'HC-ZS-001', '2025-06-01', '2026-06-10', 'approved', (SELECT id FROM users WHERE username = 'cert_admin'), '2026-05-01 09:00:00', '即将到期，需提醒'),
((SELECT id FROM crews WHERE name = '李四'), (SELECT id FROM certificate_types WHERE name = 'STCW'), 'STCW', 'STCW-LS-001', '2023-01-01', '2028-01-01', 'approved', (SELECT id FROM users WHERE username = 'cert_admin'), '2026-05-01 09:00:00', '材料完整'),
((SELECT id FROM crews WHERE name = '李四'), (SELECT id FROM certificate_types WHERE name = '高级消防'), '高级消防', 'FIRE-LS-001', '2022-07-01', '2027-07-01', 'approved', (SELECT id FROM users WHERE username = 'cert_admin'), '2026-05-01 09:00:00', '材料完整'),
((SELECT id FROM crews WHERE name = '王五'), (SELECT id FROM certificate_types WHERE name = 'STCW'), 'STCW', 'STCW-WW-001', '2021-01-01', '2026-05-01', 'approved', (SELECT id FROM users WHERE username = 'cert_admin'), '2026-05-01 09:00:00', '已过期，不能匹配'),
((SELECT id FROM crews WHERE name = '赵六'), (SELECT id FROM certificate_types WHERE name = 'GMDSS'), 'GMDSS', 'GMDSS-ZL-001', '2024-03-01', '2029-03-01', 'pending', NULL, NULL, '待审核'),
((SELECT id FROM crews WHERE name = '陈七'), (SELECT id FROM certificate_types WHERE name = 'STCW'), 'STCW', 'STCW-CQ-001', '2024-01-01', '2029-01-01', 'approved', (SELECT id FROM users WHERE username = 'cert_admin'), '2026-05-01 09:00:00', '材料完整'),
((SELECT id FROM crews WHERE name = '周八'), (SELECT id FROM certificate_types WHERE name = 'STCW'), 'STCW', 'STCW-ZB-001', '2023-03-01', '2028-03-01', 'approved', (SELECT id FROM users WHERE username = 'cert_admin'), '2026-05-01 09:00:00', '材料完整'),
((SELECT id FROM crews WHERE name = '周八'), (SELECT id FROM certificate_types WHERE name = '高级消防'), '高级消防', 'FIRE-ZB-001', '2023-03-01', '2028-03-01', 'approved', (SELECT id FROM users WHERE username = 'cert_admin'), '2026-05-01 09:00:00', '材料完整'),
((SELECT id FROM crews WHERE name = '吴九'), (SELECT id FROM certificate_types WHERE name = 'STCW'), 'STCW', 'STCW-WJ-001', '2024-02-01', '2029-02-01', 'approved', (SELECT id FROM users WHERE username = 'cert_admin'), '2026-05-01 09:00:00', '材料完整'),
((SELECT id FROM crews WHERE name = '郑十'), (SELECT id FROM certificate_types WHERE name = 'STCW'), 'STCW', 'STCW-ZT-001', '2024-02-01', '2029-02-01', 'rejected', (SELECT id FROM users WHERE username = 'cert_admin'), '2026-05-01 09:00:00', '扫描件不清晰');

INSERT INTO certificate_review_records (certificate_id, reviewer_user_id, old_status, new_status, remark) VALUES
((SELECT id FROM certificates WHERE certificate_no = 'STCW-ZS-001'), (SELECT id FROM users WHERE username = 'cert_admin'), 'pending', 'approved', '材料完整'),
((SELECT id FROM certificates WHERE certificate_no = 'HC-ZS-001'), (SELECT id FROM users WHERE username = 'cert_admin'), 'pending', 'approved', '即将到期，需提醒'),
((SELECT id FROM certificates WHERE certificate_no = 'STCW-ZT-001'), (SELECT id FROM users WHERE username = 'cert_admin'), 'pending', 'rejected', '扫描件不清晰');

INSERT INTO job_demands (
    owner_user_id, ship_id, route_id, position_id, title, ship_name, route,
    required_position, headcount, onboard_at, status
) VALUES
((SELECT id FROM users WHERE username = 'owner'), (SELECT id FROM ships WHERE name = '东方一号'), (SELECT id FROM routes WHERE route_name = '中近洋补给线'), (SELECT id FROM positions WHERE name = '水手'), '东方一号水手补员', '东方一号', '上海港-新加坡港', '水手', 1, '2026-06-01 08:00:00', 'open'),
((SELECT id FROM users WHERE username = 'owner'), (SELECT id FROM ships WHERE name = '东方二号'), (SELECT id FROM routes WHERE route_name = '远洋集装箱线'), (SELECT id FROM positions WHERE name = '机工'), '东方二号机工派遣', '东方二号', '青岛港-鹿特丹港', '机工', 1, '2026-06-05 08:00:00', 'matched'),
((SELECT id FROM users WHERE username = 'owner'), (SELECT id FROM ships WHERE name = '东方一号'), (SELECT id FROM routes WHERE route_name = '东南亚散货线'), (SELECT id FROM positions WHERE name = '船长'), '东南亚船长需求', '东方一号', '宁波舟山港-新加坡港', '船长', 1, '2026-06-12 08:00:00', 'open'),
((SELECT id FROM users WHERE username = 'other_owner'), (SELECT id FROM ships WHERE name = '北海远航'), (SELECT id FROM routes WHERE route_name = '欧洲回程线'), (SELECT id FROM positions WHERE name = '大副'), '欧洲回程大副', '北海远航', '鹿特丹港-上海港', '大副', 1, '2026-06-15 08:00:00', 'open'),
((SELECT id FROM users WHERE username = 'owner'), (SELECT id FROM ships WHERE name = '东方二号'), (SELECT id FROM routes WHERE route_name = '中近洋补给线'), (SELECT id FROM positions WHERE name = '水手'), '已完成水手派遣', '东方二号', '上海港-新加坡港', '水手', 1, '2026-04-01 08:00:00', 'closed'),
((SELECT id FROM users WHERE username = 'other_owner'), (SELECT id FROM ships WHERE name = '海晟88'), (SELECT id FROM routes WHERE route_name = '东南亚散货线'), (SELECT id FROM positions WHERE name = '机工'), '取消案例机工需求', '海晟88', '宁波舟山港-新加坡港', '机工', 1, '2026-05-10 08:00:00', 'open');

INSERT INTO job_required_certificates (job_id, certificate_type_id, certificate_type) VALUES
((SELECT id FROM job_demands WHERE title = '东方一号水手补员'), (SELECT id FROM certificate_types WHERE name = 'STCW'), 'STCW'),
((SELECT id FROM job_demands WHERE title = '东方一号水手补员'), (SELECT id FROM certificate_types WHERE name = '健康证'), '健康证'),
((SELECT id FROM job_demands WHERE title = '东方二号机工派遣'), (SELECT id FROM certificate_types WHERE name = 'STCW'), 'STCW'),
((SELECT id FROM job_demands WHERE title = '东方二号机工派遣'), (SELECT id FROM certificate_types WHERE name = '高级消防'), '高级消防'),
((SELECT id FROM job_demands WHERE title = '东南亚船长需求'), (SELECT id FROM certificate_types WHERE name = 'STCW'), 'STCW'),
((SELECT id FROM job_demands WHERE title = '欧洲回程大副'), (SELECT id FROM certificate_types WHERE name = 'GMDSS'), 'GMDSS'),
((SELECT id FROM job_demands WHERE title = '已完成水手派遣'), (SELECT id FROM certificate_types WHERE name = 'STCW'), 'STCW'),
((SELECT id FROM job_demands WHERE title = '取消案例机工需求'), (SELECT id FROM certificate_types WHERE name = 'STCW'), 'STCW');

INSERT INTO dispatches (job_id, crew_id, status, created_by_user_id, confirmed_by_user_id, created_at, updated_at) VALUES
((SELECT id FROM job_demands WHERE title = '东方二号机工派遣'), (SELECT id FROM crews WHERE name = '李四'), 'onboard', (SELECT id FROM users WHERE username = 'manager'), (SELECT id FROM users WHERE username = 'owner'), '2026-05-20 10:00:00', '2026-05-22 08:00:00'),
((SELECT id FROM job_demands WHERE title = '已完成水手派遣'), (SELECT id FROM crews WHERE name = '张三'), 'offboard', (SELECT id FROM users WHERE username = 'manager'), (SELECT id FROM users WHERE username = 'owner'), '2026-03-20 10:00:00', '2026-04-20 18:00:00'),
((SELECT id FROM job_demands WHERE title = '欧洲回程大副'), (SELECT id FROM crews WHERE name = '赵六'), 'pending_owner', (SELECT id FROM users WHERE username = 'manager'), NULL, '2026-05-28 10:00:00', '2026-05-28 10:00:00'),
((SELECT id FROM job_demands WHERE title = '取消案例机工需求'), (SELECT id FROM crews WHERE name = '郑十'), 'cancelled', (SELECT id FROM users WHERE username = 'manager'), NULL, '2026-05-09 10:00:00', '2026-05-09 12:00:00');

INSERT INTO dispatch_status_logs (dispatch_id, old_status, new_status, operator_user_id, remark, created_at) VALUES
((SELECT id FROM dispatches WHERE job_id = (SELECT id FROM job_demands WHERE title = '东方二号机工派遣')), NULL, 'pending_owner', (SELECT id FROM users WHERE username = 'manager'), '业务经理发起派遣', '2026-05-20 10:00:00'),
((SELECT id FROM dispatches WHERE job_id = (SELECT id FROM job_demands WHERE title = '东方二号机工派遣')), 'pending_owner', 'confirmed', (SELECT id FROM users WHERE username = 'owner'), '船东确认', '2026-05-21 09:00:00'),
((SELECT id FROM dispatches WHERE job_id = (SELECT id FROM job_demands WHERE title = '东方二号机工派遣')), 'confirmed', 'onboard', (SELECT id FROM users WHERE username = 'manager'), '确认上船', '2026-05-22 08:00:00'),
((SELECT id FROM dispatches WHERE job_id = (SELECT id FROM job_demands WHERE title = '已完成水手派遣')), NULL, 'pending_owner', (SELECT id FROM users WHERE username = 'manager'), '业务经理发起派遣', '2026-03-20 10:00:00'),
((SELECT id FROM dispatches WHERE job_id = (SELECT id FROM job_demands WHERE title = '已完成水手派遣')), 'pending_owner', 'confirmed', (SELECT id FROM users WHERE username = 'owner'), '船东确认', '2026-03-21 09:00:00'),
((SELECT id FROM dispatches WHERE job_id = (SELECT id FROM job_demands WHERE title = '已完成水手派遣')), 'confirmed', 'onboard', (SELECT id FROM users WHERE username = 'manager'), '确认上船', '2026-04-01 08:00:00'),
((SELECT id FROM dispatches WHERE job_id = (SELECT id FROM job_demands WHERE title = '已完成水手派遣')), 'onboard', 'offboard', (SELECT id FROM users WHERE username = 'manager'), '确认下船', '2026-04-20 18:00:00'),
((SELECT id FROM dispatches WHERE job_id = (SELECT id FROM job_demands WHERE title = '欧洲回程大副')), NULL, 'pending_owner', (SELECT id FROM users WHERE username = 'manager'), '等待船东确认', '2026-05-28 10:00:00'),
((SELECT id FROM dispatches WHERE job_id = (SELECT id FROM job_demands WHERE title = '取消案例机工需求')), NULL, 'pending_owner', (SELECT id FROM users WHERE username = 'manager'), '业务经理发起派遣', '2026-05-09 10:00:00'),
((SELECT id FROM dispatches WHERE job_id = (SELECT id FROM job_demands WHERE title = '取消案例机工需求')), 'pending_owner', 'cancelled', (SELECT id FROM users WHERE username = 'manager'), '证书审核未通过，取消派遣', '2026-05-09 12:00:00');

INSERT INTO voyage_records (dispatch_id, crew_id, job_id, ship_name, route, position, onboard_at, offboard_at, status) VALUES
((SELECT id FROM dispatches WHERE job_id = (SELECT id FROM job_demands WHERE title = '东方二号机工派遣')),
 (SELECT id FROM crews WHERE name = '李四'),
 (SELECT id FROM job_demands WHERE title = '东方二号机工派遣'),
 '东方二号', '青岛港-鹿特丹港', '机工', '2026-05-22 08:00:00', NULL, 'onboard'),
((SELECT id FROM dispatches WHERE job_id = (SELECT id FROM job_demands WHERE title = '已完成水手派遣')),
 (SELECT id FROM crews WHERE name = '张三'),
 (SELECT id FROM job_demands WHERE title = '已完成水手派遣'),
 '东方二号', '上海港-新加坡港', '水手', '2026-04-01 08:00:00', '2026-04-20 18:00:00', 'offboard');

INSERT INTO operation_logs (user_id, username, action, target_type, target_id, detail, created_at) VALUES
((SELECT id FROM users WHERE username = 'cert_admin'), 'cert_admin', 'review', 'certificate', (SELECT id FROM certificates WHERE certificate_no = 'STCW-ZS-001'), '证书审核通过', '2026-05-01 09:00:00'),
((SELECT id FROM users WHERE username = 'manager'), 'manager', 'create', 'dispatch', (SELECT id FROM dispatches WHERE job_id = (SELECT id FROM job_demands WHERE title = '东方二号机工派遣')), '发起东方二号机工派遣', '2026-05-20 10:00:00'),
((SELECT id FROM users WHERE username = 'owner'), 'owner', 'confirm', 'dispatch', (SELECT id FROM dispatches WHERE job_id = (SELECT id FROM job_demands WHERE title = '东方二号机工派遣')), '船东确认派遣', '2026-05-21 09:00:00');

CREATE OR REPLACE VIEW v_crew_certificate_status AS
SELECT
    c.id AS crew_id,
    c.name AS crew_name,
    c.position AS position,
    cert.certificate_type AS certificate_type,
    cert.certificate_no AS certificate_no,
    cert.review_status AS review_status,
    cert.expires_at AS expires_at,
    CASE
        WHEN cert.expires_at < CURRENT_DATE THEN 'expired'
        WHEN cert.expires_at <= DATE_ADD(CURRENT_DATE, INTERVAL 30 DAY) THEN 'expiring_soon'
        ELSE 'valid'
    END AS validity_status
FROM crews c
LEFT JOIN certificates cert ON cert.crew_id = c.id;

CREATE OR REPLACE VIEW v_dispatch_flow_stats AS
SELECT
    status,
    COUNT(*) AS dispatch_count
FROM dispatches
GROUP BY status;

CREATE OR REPLACE VIEW v_route_workload AS
SELECT
    CONCAT(dp.name, '-', ap.name) AS route,
    COUNT(v.id) AS voyage_count,
    SUM(CASE WHEN v.status = 'onboard' THEN 1 ELSE 0 END) AS onboard_count,
    SUM(CASE WHEN v.status = 'offboard' THEN 1 ELSE 0 END) AS offboard_count
FROM routes r
JOIN ports dp ON dp.id = r.departure_port_id
JOIN ports ap ON ap.id = r.destination_port_id
LEFT JOIN voyage_records v ON v.route = CONCAT(dp.name, '-', ap.name)
GROUP BY r.id, dp.name, ap.name;

CREATE OR REPLACE VIEW v_job_match_overview AS
SELECT
    jd.id AS job_id,
    jd.title AS job_title,
    jd.required_position,
    jd.status AS job_status,
    COUNT(DISTINCT c.id) AS available_position_crews,
    COUNT(DISTINCT jrc.id) AS required_certificate_count
FROM job_demands jd
LEFT JOIN crews c
    ON c.position = jd.required_position
   AND c.status = 'available'
LEFT JOIN job_required_certificates jrc
    ON jrc.job_id = jd.id
GROUP BY jd.id, jd.title, jd.required_position, jd.status;
