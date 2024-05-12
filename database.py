import asyncio
import aiosqlite


class Database:
    def __init__(self, loop: asyncio.AbstractEventLoop):
        self.conn, self.loop = None, loop
        self.test_mode = False  # Set to True to print while testing



    # CONNESSIONI E GESTIONI BASSO LIVELLO
    async def connect(self):
        self.conn = await aiosqlite.connect('data/maindb.db', loop=self.loop)
        await self.execute('CREATE TABLE IF NOT EXISTS users (`ID` INTEGER PRIMARY KEY AUTOINCREMENT , `chat_id` BIGINT(15) NOT NULL, `beTagged` BOOLEAN DEFAULT TRUE);', [], commit=True)
        return self.conn

    async def execute(self, sql: str, values: tuple, commit: bool = False, fetch: int = 0):
        # If no connection is established, connect
        if not self.conn:
            await self.connect()
            await asyncio.sleep(0.1)

        # Test mode, print sql and values
        if self.test_mode:
            print(sql, values)

        # Execute the query
        try:
            cursor = await self.conn.cursor()
        except aiosqlite.ProgrammingError:
            await self.connect()
            cursor = await self.conn.cursor()

        try:
            executed = await cursor.execute(sql, values)
        except aiosqlite.ProgrammingError:
            await self.connect()
            executed = await cursor.execute(sql, values)


        # If fetch is True, return the result
        fetch = await cursor.fetchone() if fetch == 1 else await cursor.rowcount() if fetch == 2 else await cursor.fetchall() if fetch == 3 else None


        # Commit Db
        if commit:
            await self.conn.commit()

        return fetch

    async def close(self):
        await self.conn.close()



    # GESTIONE INSERIMENTI | ELIMINAZIONI
    async def adduser(self, chat_id: int):
        fc = await self.execute('SELECT * FROM users WHERE chat_id = ?', (chat_id,), fetch=1)
        if not fc:
            await self.execute('INSERT INTO users (chat_id) VALUES (?)', (chat_id,), commit=True)
        return True if not fc else False

    # WRAPPER GET
    async def getBeTagged(self, chat_id: int):
        return await self.execute('SELECT beTagged FROM users WHERE chat_id = ?', (chat_id,), fetch=1)


    # WRAPPER UPDATE
    async def updateBeTagged(self, beTagged: str, chat_id: int):
        await self.execute('UPDATE users SET beTagged = ? WHERE chat_id = ?', (beTagged, chat_id, ), commit=True)
