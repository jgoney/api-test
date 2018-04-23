conn = new Mongo();
db = conn.getDB("api");

// Create indices for text search
db.songs.createIndex( { artist: "text", title: "text" } );
