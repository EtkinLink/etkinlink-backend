
CREATE TABLE universities (
  id            BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  name          VARCHAR(200) NOT NULL,
  UNIQUE KEY uq_university_name (name)
) ENGINE=InnoDB;


CREATE TABLE users (
  id              BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  name            VARCHAR(120) NOT NULL,
  username        VARCHAR(60)  NOT NULL,
  email           VARCHAR(254) NOT NULL,
  password_hash   VARBINARY(100) NOT NULL,   
  photo_url       VARCHAR(500),              
  latitude        DECIMAL(9,6),              
  longitude       DECIMAL(9,6),
  role            ENUM('USER','ADMIN') NOT NULL DEFAULT 'USER',
  university_id   BIGINT UNSIGNED,


  CONSTRAINT fk_users_university
    FOREIGN KEY (university_id) REFERENCES universities(id)
      ON UPDATE CASCADE ON DELETE SET NULL,

  UNIQUE KEY uq_users_username (username),
  UNIQUE KEY uq_users_email (email)
) ENGINE=InnoDB;


CREATE TABLE event_types (
  id   BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  code VARCHAR(40) NOT NULL,           
  UNIQUE KEY uq_event_type_code (code)
) ENGINE=InnoDB;


CREATE TABLE events (
  id              BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  owner_user_id   BIGINT UNSIGNED NOT NULL,  
  title           VARCHAR(200) NOT NULL,
  explanation     TEXT NOT NULL,
  type_id         BIGINT UNSIGNED,               
  price           DECIMAL(10,2) NOT NULL,
  starts_at       DATETIME NOT NULL,
  photo_url       VARCHAR(500),
  status          ENUM('FUTURE','COMPLETED') NOT NULL DEFAULT 'FUTURE',
  user_limit      INT UNSIGNED,              
  latitude        DECIMAL(9,6),
  longitude       DECIMAL(9,6),


  CONSTRAINT fk_events_owner
    FOREIGN KEY (owner_user_id) REFERENCES users(id)
      ON UPDATE CASCADE ON DELETE RESTRICT,

  CONSTRAINT fk_events_type
     FOREIGN KEY (type_id) REFERENCES event_types(id)
       ON UPDATE CASCADE ON DELETE SET NULL,

  INDEX idx_events_owner (owner_user_id),
  INDEX idx_events_starts_at (starts_at),
  INDEX idx_events_status (status)
) ENGINE=InnoDB;

CREATE TABLE applications (
  id            BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  event_id      BIGINT UNSIGNED NOT NULL,
  user_id       BIGINT UNSIGNED NOT NULL,
  why_me        TEXT,
  status        ENUM('PENDING','APPROVED') NOT NULL DEFAULT 'PENDING',

  CONSTRAINT fk_apps_event
    FOREIGN KEY (event_id) REFERENCES events(id)
      ON UPDATE CASCADE ON DELETE CASCADE,

  CONSTRAINT fk_apps_user
    FOREIGN KEY (user_id)  REFERENCES users(id)
      ON UPDATE CASCADE ON DELETE CASCADE,

  UNIQUE KEY uq_application_event_user (event_id, user_id),

  INDEX idx_applications_status (status)
) ENGINE=InnoDB;

CREATE TABLE participants (
  id              BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  event_id        BIGINT UNSIGNED NOT NULL,
  user_id         BIGINT UNSIGNED NOT NULL,
  application_id  BIGINT UNSIGNED, 
  status          ENUM('ATTENDED','NO_SHOW') NOT NULL DEFAULT 'NO_SHOW',

  CONSTRAINT fk_participants_event
    FOREIGN KEY (event_id) REFERENCES events(id)
      ON UPDATE CASCADE ON DELETE CASCADE,

  CONSTRAINT fk_participants_user
    FOREIGN KEY (user_id) REFERENCES users(id)
      ON UPDATE CASCADE ON DELETE CASCADE,

  CONSTRAINT fk_participants_application
    FOREIGN KEY (application_id) REFERENCES applications(id)
      ON UPDATE CASCADE ON DELETE SET NULL,

  UNIQUE KEY uq_participant_event_user (event_id, user_id),

  INDEX idx_participants_status (status)
) ENGINE=InnoDB;


CREATE TABLE ratings (
  id          BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  event_id    BIGINT UNSIGNED NOT NULL,
  user_id     BIGINT UNSIGNED NOT NULL,
  rating      TINYINT UNSIGNED NOT NULL,
  comment     TEXT,


  CONSTRAINT fk_ratings_event
    FOREIGN KEY (event_id) REFERENCES events(id)
      ON UPDATE CASCADE ON DELETE CASCADE,

  CONSTRAINT fk_ratings_user
    FOREIGN KEY (user_id)  REFERENCES users(id)
      ON UPDATE CASCADE ON DELETE CASCADE,

  
  UNIQUE KEY uq_rating_event_user (event_id, user_id)

) ENGINE=InnoDB;


