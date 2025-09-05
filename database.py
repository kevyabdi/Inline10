"""
Database Operations with MongoDB
"""

import logging
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import DuplicateKeyError
from config import Config
from typing import List, Dict, Any, Optional
import re
from datetime import datetime

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.client = None
        self.db = None
        self.collection = None
        
    async def connect(self):
        """Connect to MongoDB"""
        try:
            self.client = AsyncIOMotorClient(Config.DATABASE_URI)
            self.db = self.client[Config.DATABASE_NAME]
            self.collection = self.db[Config.COLLECTION_NAME]
            
            # Create optimized indexes for large collections
            await self.collection.create_index([("file_name", "text"), ("caption", "text")])
            await self.collection.create_index("file_unique_id", unique=True)
            await self.collection.create_index("chat_id")
            await self.collection.create_index("message_id")
            await self.collection.create_index([("date", -1)])  # For recent media queries
            await self.collection.create_index([("file_type", 1), ("date", -1)])  # Compound index for type + date
            await self.collection.create_index("file_name")  # Additional index for filename searches
            
            logger.info("Connected to MongoDB successfully")
            
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise
    
    async def disconnect(self):
        """Disconnect from MongoDB"""
        if self.client:
            self.client.close()
            logger.info("Disconnected from MongoDB")
    
    def close(self):
        """Close database connection (sync version for bot.stop)"""
        if self.client:
            self.client.close()
            logger.info("Database connection closed")
    
    async def save_media(self, media_data: Dict[str, Any]) -> bool:
        """Save media information to database"""
        try:
            await self.collection.insert_one(media_data)
            return True
        except DuplicateKeyError:
            # File already exists, skip
            return False
        except Exception as e:
            logger.error(f"Error saving media: {e}")
            return False
    
    async def search_media(self, query: str, file_type: str = None) -> List[Dict[str, Any]]:
        """Search media by query with optimization for large datasets"""
        try:
            # Create search filter
            search_filter = {}
            
            # Add file type filter if specified (use compound index)
            if file_type:
                search_filter["file_type"] = file_type
            
            # Text search in file name and caption
            if query.strip():
                # Use more efficient regex patterns
                escaped_query = re.escape(query.strip())
                
                # Prioritize exact matches and prefix matches for better performance
                or_conditions = [
                    {"file_name": {"$regex": f"^{escaped_query}", "$options": "i"}},  # Prefix match (faster)
                    {"file_name": {"$regex": escaped_query, "$options": "i"}},       # Full text match
                ]
                
                # Add caption search only if query is longer than 3 characters (avoid too broad searches)
                if len(query.strip()) > 3:
                    or_conditions.extend([
                        {"caption": {"$regex": f"^{escaped_query}", "$options": "i"}},
                        {"caption": {"$regex": escaped_query, "$options": "i"}}
                    ])
                
                search_filter["$or"] = or_conditions
            
            # Use projection to reduce memory usage - only fetch needed fields
            projection = {
                "file_id": 1,
                "file_name": 1,
                "file_size": 1,
                "file_type": 1,
                "caption": 1,
                "date": 1
            }
            
            # Execute search with optimizations
            cursor = self.collection.find(
                search_filter, 
                projection
            ).sort("date", -1).limit(Config.MAX_RESULTS)
            
            results = await cursor.to_list(length=Config.MAX_RESULTS)
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching media: {e}")
            return []
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        try:
            total_files = await self.collection.count_documents({})
            
            # Count by file type
            pipeline = [
                {"$group": {"_id": "$file_type", "count": {"$sum": 1}}}
            ]
            
            type_counts = {}
            async for doc in self.collection.aggregate(pipeline):
                type_counts[doc["_id"]] = doc["count"]
            
            return {
                "total_files": total_files,
                "by_type": type_counts
            }
            
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {"total_files": 0, "by_type": {}}
    
    async def delete_media(self, chat_id: int, message_id: int) -> bool:
        """Delete media from database"""
        try:
            result = await self.collection.delete_one({
                "chat_id": chat_id,
                "message_id": message_id
            })
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Error deleting media: {e}")
            return False
    
    async def get_total_size(self) -> int:
        """Get total size of all files in bytes"""
        try:
            pipeline = [
                {"$group": {"_id": None, "total_size": {"$sum": "$file_size"}}}
            ]
            
            result = await self.collection.aggregate(pipeline).to_list(1)
            return result[0]["total_size"] if result else 0
            
        except Exception as e:
            logger.error(f"Error getting total size: {e}")
            return 0
    
    async def get_recent_media(self, limit: int = 25) -> List[Dict[str, Any]]:
        """Get recent media files, optimized for large collections"""
        try:
            # Use compound index for better performance on large collections
            projection = {
                "file_id": 1,
                "file_name": 1,
                "file_size": 1,
                "file_type": 1,
                "caption": 1,
                "date": 1
            }
            
            # Get recent videos first (most requested content type)
            video_cursor = self.collection.find(
                {"file_type": "video"},
                projection
            ).sort("date", -1).limit(limit)
            
            results = await video_cursor.to_list(length=limit)
            
            # If we don't have enough videos, fill with other media types
            if len(results) < limit:
                remaining_limit = limit - len(results)
                # Skip already fetched video file_ids to avoid duplicates
                video_ids = [r["file_id"] for r in results]
                
                other_cursor = self.collection.find(
                    {
                        "file_type": {"$ne": "video"},
                        "file_id": {"$nin": video_ids}
                    },
                    projection
                ).sort("date", -1).limit(remaining_limit)
                
                other_results = await other_cursor.to_list(length=remaining_limit)
                results.extend(other_results)
            
            return results
            
        except Exception as e:
            logger.error(f"Error getting recent media: {e}")
            return []
    
    async def get_recent_videos(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent videos specifically for empty queries"""
        try:
            projection = {
                "file_id": 1,
                "file_name": 1,
                "file_size": 1,
                "file_type": 1,
                "caption": 1,
                "date": 1
            }
            
            # Get only videos, sorted by most recent
            cursor = self.collection.find(
                {"file_type": "video"},
                projection
            ).sort("date", -1).limit(limit)
            
            results = await cursor.to_list(length=limit)
            return results
            
        except Exception as e:
            logger.error(f"Error getting recent videos: {e}")
            return []
    
    async def ban_user(self, user_id: int) -> bool:
        """Ban a user from using the bot"""
        try:
            banned_collection = self.db["banned_users"]
            await banned_collection.update_one(
                {"user_id": user_id},
                {"$set": {"user_id": user_id, "banned_at": datetime.now()}},
                upsert=True
            )
            return True
        except Exception as e:
            logger.error(f"Error banning user {user_id}: {e}")
            return False
    
    async def unban_user(self, user_id: int) -> bool:
        """Unban a user"""
        try:
            banned_collection = self.db["banned_users"]
            await banned_collection.delete_one({"user_id": user_id})
            return True
        except Exception as e:
            logger.error(f"Error unbanning user {user_id}: {e}")
            return False
    
    async def is_banned(self, user_id: int) -> bool:
        """Check if a user is banned"""
        try:
            banned_collection = self.db["banned_users"]
            result = await banned_collection.find_one({"user_id": user_id})
            return result is not None
        except Exception as e:
            logger.error(f"Error checking if user {user_id} is banned: {e}")
            return False
    
    async def get_user_count(self) -> int:
        """Get total number of users who have used the bot"""
        try:
            users_collection = self.db["users"]
            return await users_collection.count_documents({})
        except Exception as e:
            logger.error(f"Error getting user count: {e}")
            return 0
    
    async def add_user(self, user_id: int, username: str = None, first_name: str = None) -> bool:
        """Add user to database"""
        try:
            users_collection = self.db["users"]
            await users_collection.update_one(
                {"user_id": user_id},
                {
                    "$set": {
                        "user_id": user_id,
                        "username": username,
                        "first_name": first_name,
                        "last_seen": datetime.now()
                    },
                    "$inc": {"search_count": 0}  # Initialize search count
                },
                upsert=True
            )
            return True
        except Exception as e:
            logger.error(f"Error adding user {user_id}: {e}")
            return False
    
    async def log_search_query(self, user_id: int, query: str, username: str = None) -> bool:
        """Log search query for analytics"""
        try:
            # Log the search query
            search_logs_collection = self.db["search_logs"]
            await search_logs_collection.insert_one({
                "user_id": user_id,
                "username": username,
                "query": query.strip().lower(),
                "timestamp": datetime.now()
            })
            
            # Increment user's search count
            users_collection = self.db["users"]
            await users_collection.update_one(
                {"user_id": user_id},
                {"$inc": {"search_count": 1}},
                upsert=True
            )
            
            return True
        except Exception as e:
            logger.error(f"Error logging search query: {e}")
            return False
    
    async def get_top_searched_movies(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top searched movie queries"""
        try:
            search_logs_collection = self.db["search_logs"]
            
            # Aggregate search queries
            pipeline = [
                {"$match": {"query": {"$ne": ""}}},  # Exclude empty queries
                {"$group": {
                    "_id": "$query",
                    "search_count": {"$sum": 1},
                    "last_searched": {"$max": "$timestamp"}
                }},
                {"$sort": {"search_count": -1}},
                {"$limit": limit}
            ]
            
            results = []
            async for doc in search_logs_collection.aggregate(pipeline):
                results.append({
                    "query": doc["_id"],
                    "search_count": doc["search_count"],
                    "last_searched": doc["last_searched"]
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Error getting top searched movies: {e}")
            return []
    
    async def get_most_active_users(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get most active users by search count"""
        try:
            users_collection = self.db["users"]
            
            cursor = users_collection.find(
                {"search_count": {"$gt": 0}},
                {"user_id": 1, "username": 1, "first_name": 1, "search_count": 1, "last_seen": 1}
            ).sort("search_count", -1).limit(limit)
            
            results = []
            async for user in cursor:
                results.append({
                    "user_id": user["user_id"],
                    "username": user.get("username"),
                    "first_name": user.get("first_name"),
                    "search_count": user.get("search_count", 0),
                    "last_seen": user.get("last_seen")
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Error getting most active users: {e}")
            return []
    
    async def log_not_found_search(self, user_id: int, query: str, username: str = None) -> bool:
        """Log search query that returned no results"""
        try:
            not_found_collection = self.db["not_found_searches"]
            await not_found_collection.insert_one({
                "user_id": user_id,
                "username": username,
                "query": query.strip().lower(),
                "timestamp": datetime.now()
            })
            return True
        except Exception as e:
            logger.error(f"Error logging not found search: {e}")
            return False
    
    async def get_most_searched_not_found(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get most searched queries that returned no results"""
        try:
            not_found_collection = self.db["not_found_searches"]
            
            pipeline = [
                {"$match": {"query": {"$ne": ""}}},  # Exclude empty queries
                {"$group": {
                    "_id": "$query",
                    "search_count": {"$sum": 1},
                    "last_searched": {"$max": "$timestamp"},
                    "users_searched": {"$addToSet": "$user_id"}
                }},
                {"$addFields": {
                    "unique_users": {"$size": "$users_searched"}
                }},
                {"$sort": {"search_count": -1}},
                {"$limit": limit}
            ]
            
            results = []
            async for doc in not_found_collection.aggregate(pipeline):
                results.append({
                    "query": doc["_id"],
                    "search_count": doc["search_count"],
                    "unique_users": doc["unique_users"],
                    "last_searched": doc["last_searched"]
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Error getting most searched not found: {e}")
            return []