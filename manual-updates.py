import pymysql

queries = ["UPDATE silverstrike_transaction st SET st.amount = (SELECT SUM(ss.amount) FROM silverstrike_split ss, silverstrike_account sa WHERE ss.transaction_id = st.id and sa.id = ss.account_id and sa.account_type = 1 AND st.transaction_type != 3 GROUP BY st.id) WHERE id in (select id from (SELECT st.id, st.amount, SUM(ss.amount), st.amount - SUM(ss.amount) FROM silverstrike_transaction st, silverstrike_split ss, silverstrike_account sa WHERE ss.transaction_id = st.id and sa.id = ss.account_id and sa.account_type = 1 AND st.transaction_type != 3 GROUP BY st.id HAVING st.amount - SUM(ss.amount)) temp);","DELETE IGNORE FROM silverstrike_account where id not IN (select opposing_account_id as id from silverstrike_split union select account_id from silverstrike_split) and account_type = '2';"]


host = "rachael.skynet.com"
port = 3306
user = "speedy"
passwd = "Nikto0918"
dbname = "silverstrike"


conn = pymysql.connect(host=host, port=port, user=user, password=passwd, database=dbname)
cursor = conn.cursor()
for query in queries:
	result = cursor.execute(query)
	conn.commit()
	print("%s results have been updated" % result)
