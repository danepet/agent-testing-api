import aiohttp
import json
import uuid
from typing import Dict, Any, Optional

from app.core.config import settings


class AgentService:
    """Service for interacting with the Salesforce AI Agent API."""
    
    def __init__(self):
        self.sessions = {}  # Store active sessions
    
    async def start_session(self, test_id: str, credentials: Dict[str, str]) -> str:
        """
        Start a new session with the AI Agent.
        
        Args:
            test_id: ID of the test being executed
            credentials: Salesforce credentials for connecting to the agent
            
        Returns:
            str: Session ID
        """
        org_domain = credentials.get("sf_org_domain")
        client_id = credentials.get("sf_client_id")
        client_secret = credentials.get("sf_client_secret")
        agent_id = credentials.get("sf_agent_id")
        
        # Validate credentials
        if not all([org_domain, client_id, client_secret, agent_id]):
            raise ValueError("Missing required agent credentials")
        
        # Get auth token for Salesforce
        auth_token = await self._get_auth_token(org_domain, client_id, client_secret)
        
        # Start a session with the agent
        api_url = f"{org_domain}/einstein/ai-agent/v1/agents/{agent_id}/sessions"
        
        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Bearer {auth_token}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "externalSessionKey": f"test_{test_id}_{uuid.uuid4()}",
                "instanceConfig": {
                    "endpoint": org_domain
                },
                "variables": [],
                "streamingCapabilities": {
                    "chunkTypes": ["Text"]
                },
                "bypassUser": True
            }
            
            async with session.post(api_url, headers=headers, json=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Failed to start agent session: {error_text}")
                
                response_data = await response.json()
                session_id = response_data.get("sessionId")
                
                if not session_id:
                    raise Exception("No session ID returned from agent")
                
                # Store session info
                self.sessions[session_id] = {
                    "auth_token": auth_token,
                    "org_domain": org_domain,
                    "agent_id": agent_id
                }
                
                return session_id
    
    async def send_message(self, session_id: str, message: str) -> str:
        """
        Send a message to the AI Agent and get a response.
        
        Args:
            session_id: Active session ID
            message: The message to send
            
        Returns:
            str: The agent's response
        """
        if session_id not in self.sessions:
            raise ValueError(f"Invalid or expired session ID: {session_id}")
        
        session_info = self.sessions[session_id]
        api_url = f"{session_info['org_domain']}/einstein/ai-agent/v1/sessions/{session_id}/messages"
        
        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Bearer {session_info['auth_token']}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "message": {
                    "sequenceId": int(uuid.uuid1().time),
                    "type": "Text",
                    "text": message
                },
                "variables": []
            }
            
            async with session.post(api_url, headers=headers, json=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Failed to send message: {error_text}")
                
                response_data = await response.json()
                
                # Extract text from response
                return self._extract_response_text(response_data)
    
    async def end_session(self, session_id: str) -> None:
        """
        End an active session with the AI Agent.
        
        Args:
            session_id: Active session ID
        """
        if session_id not in self.sessions:
            return  # Session already ended or invalid
        
        session_info = self.sessions[session_id]
        api_url = f"{session_info['org_domain']}/einstein/ai-agent/v1/sessions/{session_id}"
        
        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Bearer {session_info['auth_token']}",
                "Content-Type": "application/json",
                "x-session-end-reason": "TestCompleted"
            }
            
            try:
                async with session.delete(api_url, headers=headers) as response:
                    if response.status != 200:
                        # Log but don't raise
                        error_text = await response.text()
                        print(f"Warning: Failed to end session: {error_text}")
            except Exception as e:
                print(f"Warning: Error ending session: {str(e)}")
            finally:
                # Remove from active sessions
                if session_id in self.sessions:
                    del self.sessions[session_id]
    
    async def _get_auth_token(self, org_domain: str, client_id: str, client_secret: str) -> str:
        """
        Get an OAuth token from Salesforce.
        
        Args:
            org_domain: Salesforce org domain
            client_id: Connected App client ID
            client_secret: Connected App client secret
            
        Returns:
            str: OAuth access token
        """
        token_url = f"{org_domain}/services/oauth2/token"
        
        async with aiohttp.ClientSession() as session:
            data = {
                'grant_type': 'client_credentials',
                'client_id': client_id,
                'client_secret': client_secret
            }
            
            async with session.post(token_url, data=data) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Failed to get auth token: {error_text}")
                
                token_data = await response.json()
                return token_data.get("access_token")
    
    def _extract_response_text(self, response_data: Dict[str, Any]) -> str:
        """
        Extract text from a structured agent response.
        
        Args:
            response_data: Response from the agent API
            
        Returns:
            str: Extracted text from the response
        """
        if "messages" in response_data and len(response_data["messages"]) > 0:
            all_messages = []
            for msg in response_data["messages"]:
                if "message" in msg:
                    all_messages.append(msg["message"])
            return "\n".join(all_messages)
        return str(response_data)
