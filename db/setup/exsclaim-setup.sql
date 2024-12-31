CREATE SCHEMA IF NOT EXISTS results;

DROP TABLE IF EXISTS results.subfigurelabel CASCADE;
DROP TABLE IF EXISTS results.scalelabel CASCADE;
DROP TABLE IF EXISTS results.scale CASCADE;
DROP TABLE IF EXISTS results.subfigure CASCADE;
DROP TABLE IF EXISTS results.figure CASCADE;
DROP TABLE IF EXISTS results.article CASCADE;
DROP TABLE IF EXISTS classification_codes CASCADE;

CREATE TABLE IF NOT EXISTS classification_codes(
    name VARCHAR(12) NOT NULL,
    code CHAR(2) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS results.article(
    run_id UUID NOT NULL,
    id VARCHAR(32) NOT NULL PRIMARY KEY,
    title TEXT NOT NULL,
    url VARCHAR(200) NOT NULL,
    license VARCHAR(200) NOT NULL,
    open BOOLEAN DEFAULT FALSE,
    authors VARCHAR(350) DEFAULT NULL,
    abstract TEXT DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS results.figure(
    run_id UUID NOT NULL,
    id VARCHAR(40) NOT NULL PRIMARY KEY,
    caption TEXT NOT NULL,
    caption_delimiter VARCHAR(12),
    url VARCHAR(200) NOT NULL,
    figure_path VARCHAR(100) NOT NULL,
    article_id VARCHAR(32) NOT NULL REFERENCES results.article(id)
);

CREATE TABLE IF NOT EXISTS results.subfigure(
    run_id UUID NOT NULL,
    id VARCHAR(44) NOT NULL PRIMARY KEY,
    classification_code CHAR(2) NOT NULL REFERENCES classification_codes(code),
    height DOUBLE PRECISION DEFAULT NULL,
    width DOUBLE PRECISION DEFAULT NULL,
    nm_height DOUBLE PRECISION DEFAULT NULL,
    nm_width DOUBLE PRECISION DEFAULT NULL,
    x1 INT NOT NULL,
    y1 INT NOT NULL,
    x2 INT NOT NULL,
    y2 INT NOT NULL,
    caption TEXT DEFAULT NULL,
    keywords VARCHAR(20)[] NOT NULL,
    -- general VARCHAR(20)[] NOT NULL,
    figure_id VARCHAR(40) NOT NULL REFERENCES results.figure(id)
);

CREATE TABLE IF NOT EXISTS results.scale(
    run_id UUID NOT NULL,
    id VARCHAR(48) NOT NULL PRIMARY KEY,
    x1 INT NOT NULL,
    y1 INT NOT NULL,
    x2 INT NOT NULL,
    y2 INT NOT NULL,
    length VARCHAR(8) DEFAULT NULL,
    label_line_distance DOUBLE PRECISION DEFAULT NULL,
    confidence DOUBLE PRECISION DEFAULT NULL,
    subfigure_id VARCHAR(44) NOT NULL REFERENCES results.subfigure(id)
);

CREATE TABLE IF NOT EXISTS results.scalelabel(
    run_id UUID NOT NULL,
    text VARCHAR(15) NOT NULL,
    x1 INT NOT NULL,
    y1 INT NOT NULL,
    x2 INT NOT NULL,
    y2 INT NOT NULL,
    label_confidence DOUBLE PRECISION DEFAULT NULL,
    box_confidence DOUBLE PRECISION DEFAULT NULL,
    nm DOUBLE PRECISION DEFAULT NULL,
    scale_bar_id VARCHAR(48) NOT NULL REFERENCES results.scale(id)
);

CREATE TABLE IF NOT EXISTS results.subfigurelabel(
    run_id UUID NOT NULL,
    text VARCHAR(15) NOT NULL,
    x1 INT NOT NULL,
    y1 INT NOT NULL,
    x2 INT NOT NULL,
    y2 INT NOT NULL,
    label_confidence DOUBLE PRECISION DEFAULT NULL,
    box_confidence DOUBLE PRECISION DEFAULT NULL,
    subfigure_id VARCHAR(44) NOT NULL REFERENCES results.subfigure(id)
);


CREATE VIEW exsclaimui_article AS SELECT * FROM results.article;
CREATE VIEW exsclaimui_figure AS SELECT * FROM results.figure;
CREATE VIEW exsclaimui_subfigure AS SELECT * FROM results.subfigure;


INSERT INTO classification_codes VALUES('microscopy', 'MC');
INSERT INTO classification_codes VALUES('diffraction', 'DF');
INSERT INTO classification_codes VALUES('graph', 'GR');
INSERT INTO classification_codes VALUES('basic_photo', 'PH');
INSERT INTO classification_codes VALUES('illustration', 'IL');
INSERT INTO classification_codes VALUES('unclear', 'UN');
INSERT INTO classification_codes VALUES('parent', 'PT');