truncate table USD_JPY_1m_TABLE;
truncate table USD_JPY_5m_TABLE;
truncate table USD_JPY_1h_TABLE;
truncate table USD_JPY_day_TABLE;

truncate table AUD_JPY_1m_TABLE;
truncate table AUD_JPY_5m_TABLE;
truncate table AUD_JPY_1h_TABLE;
truncate table AUD_JPY_day_TABLE;

truncate table AUD_USD_1m_TABLE;
truncate table AUD_USD_5m_TABLE;
truncate table AUD_USD_1h_TABLE;
truncate table AUD_USD_day_TABLE;

truncate table EUR_USD_1m_TABLE;
truncate table EUR_USD_5m_TABLE;
truncate table EUR_USD_1h_TABLE;
truncate table EUR_USD_day_TABLE;

truncate table EUR_JPY_1m_TABLE;
truncate table EUR_JPY_5m_TABLE;
truncate table EUR_JPY_1h_TABLE;
truncate table EUR_JPY_day_TABLE;

truncate table GBP_JPY_1m_TABLE;
truncate table GBP_JPY_5m_TABLE;
truncate table GBP_JPY_1h_TABLE;
truncate table GBP_JPY_day_TABLE;

truncate table GBP_USD_1m_TABLE;
truncate table GBP_USD_5m_TABLE;
truncate table GBP_USD_1h_TABLE;
truncate table GBP_USD_day_TABLE;


truncate table CAD_USD_1m_TABLE;
truncate table CAD_USD_5m_TABLE;
truncate table CAD_USD_1h_TABLE;
truncate table CAD_USD_day_TABLE;

truncate table CAD_JPY_1m_TABLE;
truncate table CAD_JPY_5m_TABLE;
truncate table CAD_JPY_1h_TABLE;
truncate table CAD_JPY_day_TABLE;

create table USD_JPY_1m_TABLE(open_ask double, open_bid double, close_ask double, close_bid double, high_ask double, high_bid double, low_ask double, low_bid double, insert_time timestamp primary key);
create table USD_JPY_5m_TABLE(open_ask double, open_bid double, close_ask double, close_bid double, high_ask double, high_bid double, low_ask double, low_bid double, insert_time timestamp primary key);
create table USD_JPY_1h_TABLE(open_ask double, open_bid double, close_ask double, close_bid double, high_ask double, high_bid double, low_ask double, low_bid double, insert_time timestamp primary key);
create table USD_JPY_day_TABLE(open_ask double, open_bid double, close_ask double, close_bid double, high_ask double, high_bid double, low_ask double, low_bid double, insert_time timestamp primary key);

create table AUD_JPY_1m_TABLE(open_ask double, open_bid double, close_ask double, close_bid double, high_ask double, high_bid double, low_ask double, low_bid double, insert_time timestamp primary key);
create table AUD_JPY_5m_TABLE(open_ask double, open_bid double, close_ask double, close_bid double, high_ask double, high_bid double, low_ask double, low_bid double, insert_time timestamp primary key);
create table AUD_JPY_1h_TABLE(open_ask double, open_bid double, close_ask double, close_bid double, high_ask double, high_bid double, low_ask double, low_bid double, insert_time timestamp primary key);
create table AUD_JPY_day_TABLE(open_ask double, open_bid double, close_ask double, close_bid double, high_ask double, high_bid double, low_ask double, low_bid double, insert_time timestamp primary key);

create table EUR_USD_1m_TABLE(open_ask double, open_bid double, close_ask double, close_bid double, high_ask double, high_bid double, low_ask double, low_bid double, insert_time timestamp primary key);
create table EUR_USD_5m_TABLE(open_ask double, open_bid double, close_ask double, close_bid double, high_ask double, high_bid double, low_ask double, low_bid double, insert_time timestamp primary key);
create table EUR_USD_1h_TABLE(open_ask double, open_bid double, close_ask double, close_bid double, high_ask double, high_bid double, low_ask double, low_bid double, insert_time timestamp primary key);
create table EUR_USD_day_TABLE(open_ask double, open_bid double, close_ask double, close_bid double, high_ask double, high_bid double, low_ask double, low_bid double, insert_time timestamp primary key);

create table EUR_JPY_1m_TABLE(open_ask double, open_bid double, close_ask double, close_bid double, high_ask double, high_bid double, low_ask double, low_bid double, insert_time timestamp primary key);
create table EUR_JPY_5m_TABLE(open_ask double, open_bid double, close_ask double, close_bid double, high_ask double, high_bid double, low_ask double, low_bid double, insert_time timestamp primary key);
create table EUR_JPY_1h_TABLE(open_ask double, open_bid double, close_ask double, close_bid double, high_ask double, high_bid double, low_ask double, low_bid double, insert_time timestamp primary key);
create table EUR_JPY_day_TABLE(open_ask double, open_bid double, close_ask double, close_bid double, high_ask double, high_bid double, low_ask double, low_bid double, insert_time timestamp primary key);

create table GBP_JPY_1m_TABLE(open_ask double, open_bid double, close_ask double, close_bid double, high_ask double, high_bid double, low_ask double, low_bid double, insert_time timestamp primary key);
create table GBP_JPY_5m_TABLE(open_ask double, open_bid double, close_ask double, close_bid double, high_ask double, high_bid double, low_ask double, low_bid double, insert_time timestamp primary key);
create table GBP_JPY_1h_TABLE(open_ask double, open_bid double, close_ask double, close_bid double, high_ask double, high_bid double, low_ask double, low_bid double, insert_time timestamp primary key);
create table GBP_JPY_day_TABLE(open_ask double, open_bid double, close_ask double, close_bid double, high_ask double, high_bid double, low_ask double, low_bid double, insert_time timestamp primary key);

create table GBP_USD_1m_TABLE(open_ask double, open_bid double, close_ask double, close_bid double, high_ask double, high_bid double, low_ask double, low_bid double, insert_time timestamp primary key);
create table GBP_USD_5m_TABLE(open_ask double, open_bid double, close_ask double, close_bid double, high_ask double, high_bid double, low_ask double, low_bid double, insert_time timestamp primary key);
create table GBP_USD_1h_TABLE(open_ask double, open_bid double, close_ask double, close_bid double, high_ask double, high_bid double, low_ask double, low_bid double, insert_time timestamp primary key);
create table GBP_USD_day_TABLE(open_ask double, open_bid double, close_ask double, close_bid double, high_ask double, high_bid double, low_ask double, low_bid double, insert_time timestamp primary key);

create table AUD_USD_1m_TABLE(open_ask double, open_bid double, close_ask double, close_bid double, high_ask double, high_bid double, low_ask double, low_bid double, insert_time timestamp primary key);
create table AUD_USD_5m_TABLE(open_ask double, open_bid double, close_ask double, close_bid double, high_ask double, high_bid double, low_ask double, low_bid double, insert_time timestamp primary key);
create table AUD_USD_1h_TABLE(open_ask double, open_bid double, close_ask double, close_bid double, high_ask double, high_bid double, low_ask double, low_bid double, insert_time timestamp primary key);
create table AUD_USD_day_TABLE(open_ask double, open_bid double, close_ask double, close_bid double, high_ask double, high_bid double, low_ask double, low_bid double, insert_time timestamp primary key);

create table CAD_USD_1m_TABLE(open_ask double, open_bid double, close_ask double, close_bid double, high_ask double, high_bid double, low_ask double, low_bid double, insert_time timestamp primary key);
create table CAD_USD_5m_TABLE(open_ask double, open_bid double, close_ask double, close_bid double, high_ask double, high_bid double, low_ask double, low_bid double, insert_time timestamp primary key);
create table CAD_USD_1h_TABLE(open_ask double, open_bid double, close_ask double, close_bid double, high_ask double, high_bid double, low_ask double, low_bid double, insert_time timestamp primary key);
create table CAD_USD_day_TABLE(open_ask double, open_bid double, close_ask double, close_bid double, high_ask double, high_bid double, low_ask double, low_bid double, insert_time timestamp primary key);

create table CAD_JPY_1m_TABLE(open_ask double, open_bid double, close_ask double, close_bid double, high_ask double, high_bid double, low_ask double, low_bid double, insert_time timestamp primary key);
create table CAD_JPY_5m_TABLE(open_ask double, open_bid double, close_ask double, close_bid double, high_ask double, high_bid double, low_ask double, low_bid double, insert_time timestamp primary key);
create table CAD_JPY_1h_TABLE(open_ask double, open_bid double, close_ask double, close_bid double, high_ask double, high_bid double, low_ask double, low_bid double, insert_time timestamp primary key);
create table CAD_JPY_day_TABLE(open_ask double, open_bid double, close_ask double, close_bid double, high_ask double, high_bid double, low_ask double, low_bid double, insert_time timestamp primary key);


