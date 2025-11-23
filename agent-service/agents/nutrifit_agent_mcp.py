"""Nutrifit Agent configuration with native MCP integration.

This module implements the multi-agent Swarm architecture using MCPClient
to load tools directly from FastMCP servers (activity, meal, nutritional-profile).

Architecture:
    FastMCP Servers (STDIO) → MCPClient → Strands Agent Tools
    
No HTTP adapter - tools are loaded directly from MCP protocol.
"""

import os
import logging
from typing import Dict, Optional, List, Any
from pathlib import Path

from strands import Agent
from strands.models.anthropic import AnthropicModel
from strands.multiagent import Swarm
from strands.tools.mcp import MCPClient
from mcp import StdioServerParameters, stdio_client

# Configure Strands logging for debugging
logging.getLogger("strands").setLevel(logging.DEBUG)
logging.getLogger("strands.tools").setLevel(logging.DEBUG)
logging.getLogger("strands.multiagent").setLevel(logging.DEBUG)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class NutrifitAgentManager:
    """Manages Nutrifit multi-agent Swarm with native MCP integration."""

    def __init__(self):
        """Initialize agent manager with MCP configuration."""
        self.swarms: Dict[str, Dict] = {}  # {user_id: {"swarm": Swarm, "mcp_clients": [...]}}
        self.user_mcp_clients: Dict[str, Dict[str, MCPClient]] = {}  # {user_id: {server_name: client}}
        
        # Environment configuration
        self.mcp_base_path = Path(os.getenv("MCP_BASE_PATH", "/app/MCP"))
        self.mcp_python_path = os.getenv("MCP_PYTHON_PATH", "/app/MCP/.venv/bin/python")
        self.graphql_endpoint = os.getenv("GRAPHQL_ENDPOINT", "http://nutrifit-backend:8080/graphql")
        
        # Anthropic Model configuration
        anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        model_id = os.getenv("STRANDS_MODEL", "claude-sonnet-4-20250514")
        
        self.anthropic_model = AnthropicModel(
            client_args={"api_key": anthropic_api_key},
            max_tokens=4096,
            model_id=model_id,
            params={"temperature": 0.7},
        )
        
        # MCP server paths
        self.mcp_servers = {
            "user": self.mcp_base_path / "user-mcp" / "server_fastmcp.py",
            "activity": self.mcp_base_path / "activity-mcp" / "server_fastmcp.py",
            "meal": self.mcp_base_path / "meal-mcp" / "server_fastmcp.py",
            "nutritional_profile": self.mcp_base_path / "nutritional-profile-mcp" / "server_fastmcp.py",
        }
        
        logger.info("✅ Nutrifit Agent Manager initialized (per-user MCP clients)")
        
        # Verify MCP servers exist
        for name, path in self.mcp_servers.items():
            if not path.exists():
                logger.warning(f"⚠️  MCP server not found: {name} at {path}")
            else:
                logger.info(f"✅ MCP server found: {name} at {path}")

    def initialize_mcp_clients(self) -> None:
        """Initialize method - now a no-op as clients are created per-user on-demand."""
        logger.info("✅ MCP initialization configured (clients created per-user with correct auth token)")

    def shutdown_mcp_clients(self) -> None:
        """Shutdown all per-user MCP clients and swarms."""
        logger.info("🛑 Shutting down all MCP clients and swarms...")
        
        # Cleanup user swarms and their MCP clients
        for user_id in list(self.swarms.keys()):
            self.cleanup_user_swarm(user_id)
        
        # Stop any remaining MCP clients
        for user_id, clients in list(self.user_mcp_clients.items()):
            for server_name, client in clients.items():
                try:
                    logger.info(f"⏳ Stopping {server_name} for user {user_id}...")
                    client.stop()
                except Exception as e:
                    logger.warning(f"⚠️  Failed to stop {server_name}: {e}")
            self.user_mcp_clients.pop(user_id, None)
        
        logger.info("✅ All MCP clients shutdown complete")

    def _create_user_mcp_clients(self, auth_token: str) -> Dict[str, MCPClient]:
        """Create MCP clients for a user with their auth token.
        
        Args:
            auth_token: JWT token for GraphQL authentication
            
        Returns:
            Dictionary of MCP clients {server_name: client}
        """
        clients = {}
        
        for server_name in ["user", "activity", "meal", "nutritional_profile"]:
            try:
                server_path = self.mcp_servers.get(server_name)
                if not server_path or not server_path.exists():
                    logger.error(f"❌ MCP server not found: {server_name}")
                    continue
                
                # Configure STDIO transport with user's auth token
                server_params = StdioServerParameters(
                    command=self.mcp_python_path,
                    args=[str(server_path)],
                    env={
                        "GRAPHQL_ENDPOINT": self.graphql_endpoint,
                        "AUTH0_TOKEN": auth_token,
                    }
                )
                
                # Create transport factory (closure to capture params)
                transport_factory = lambda params=server_params: stdio_client(params)
                
                # Create and start MCP client
                mcp_client = MCPClient(transport_factory)
                logger.info(f"⏳ Starting {server_name} MCP client with user token...")
                mcp_client.start()
                clients[server_name] = mcp_client
                logger.info(f"✅ {server_name} MCP client started")
                
            except Exception as e:
                logger.error(f"❌ Failed to create {server_name} MCP client: {e}", exc_info=True)
        
        logger.info(f"✅ Created {len(clients)}/4 MCP clients for user")
        return clients

    def _create_router_agent(self, auth_token: str, mcp_clients: Dict[str, MCPClient]) -> Agent:
        """Create Router agent with onboarding and user management tools.
        
        Args:
            auth_token: JWT token for GraphQL authentication
            mcp_clients: Dictionary of MCP clients {server_name: client}
            
        Returns:
            Router Agent instance
        """
        # Load tools from user and nutritional-profile MCPs
        tools = []
        
        # User management tools
        if "user" in mcp_clients:
            try:
                client = mcp_clients["user"]
                user_tools = client.list_tools_sync()
                # MCP tools are already configured, just add all
                tools.extend(user_tools)
                logger.info(f"✅ Router loaded {len(user_tools)} user tools")
            except Exception as e:
                logger.error(f"❌ User tool loading failed: {e}", exc_info=True)
        
        # Profile management tools
        if "nutritional_profile" in mcp_clients:
            try:
                client = mcp_clients["nutritional_profile"]
                # Client already started, list tools (subprocess alive)
                profile_tools = client.list_tools_sync()
                # MCP tools already configured, add all
                tools.extend(profile_tools)
                logger.info(f"✅ Router loaded {len(profile_tools)} profile tools for onboarding")
            except Exception as e:
                logger.error(f"❌ Router tool loading failed: {e}", exc_info=True)
        
        system_prompt = """Sei GymBro - il tuo amico fitness super motivato e diretto!

🎯 CHI SEI:
Hai 25 anni, sei un ragazzo fissato con fitness e nutrizione, parli come un amico diretto e senza peli sulla lingua.
Usi slang giovanile, chiami tutti "bro", e non hai paura di dire le cose come stanno.
Sei tipo quello che al parco ti grida "DAJE BRO, ANCORA 10 RIPETIZIONI!" 💪

🗣️ COME PARLI:
- Usa "bro", "fra", "zio", "bella", "daje", "spacca", "stra", "tipo"
- Sei diretto: "bro hai mangiato merda oggi" o "fra stai spaccando tutto!"
- Motivazionale quando serve: "continua così e ti fai un fisico della madonna!"
- A volte scurrile ma sempre con affetto: "ma che cazzo hai mangiato ieri?"
- Usa emoji: 💪 🔥 😤 💯 👊 🍕 🍔 (soprattutto quando giudichi il cibo)

📊 COSA FAI:
1. **Onboarding** - Setup profilo con `create_nutritional_profile`:
   - Chiedi: età, peso (kg), altezza (cm), sesso (M/F), livello attività, obiettivo
   - Valida: età 13-120, peso 30-300kg, altezza 100-250cm
   - activity_level: SEDENTARY|LIGHT|MODERATE|ACTIVE|VERY_ACTIVE
   - goal_type: CUT (dimagrire)|MAINTAIN (mantenere)|BULK (massa muscolare)

2. **Analisi dati e statistiche**:
   - Query profilo con `get_nutritional_profile`
   - Presenta dati con TABELLE e GRAFICI quando possibile
   - Analisi precisa ma commenti da bro: "Guarda qua bro, i dati:"
   
3. **Routing agli esperti**:
   - Pasti/alimentazione → TRANSFER a `nutrizionista` (esperto serio)
   - Allenamento/attività → TRANSFER a `personal_trainer` (coach professionista)
   - NON rispondere MAI tu su pasti/workout, manda agli esperti!

💬 ESEMPI TUO STILE:
User: "ho mangiato pizza e gelato"
Tu: "Bro... pizza E gelato? 🍕 Hai fatto un disastro oggi! Dai mando la richiesta al nutrizionista che ti fa il cazziatone come si deve"

User: "voglio dimagrire"
Tu: "Daje bro! 💪 Dimmi età, peso, altezza e quanto ti muovi così ti setto il profilo e ti facciamo spaccare!"

User: "oggi ho mangiato bene"
Tu: "Stra bravo fra! 💯 Fammi vedere i dati... [analizza] OH STAI SPACCANDO! Se continui così ti fai un fisico della madonna! 🔥"

User: "cosa ho mangiato ieri?"
Tu: "Bro aspetta che chiedo al nutrizionista, lui ha i dati precisi" → TRANSFER

🎯 REGOLE:
- Tabelle/grafici per dati numerici (calorie, macro, progressi)
- Commenti diretti su performance: 🔥 top / 💩 pessimo
- SEMPRE trasferisci domande su pasti/workout agli esperti
- Mantieni tono amichevole anche quando giudichi
- ITALIANO sempre, slang giovane"""

        return Agent(
            name="nutrifit_router",
            model=self.anthropic_model,
            tools=tools,
            system_prompt=system_prompt,
        )

    def _create_nutritionist_agent(self, auth_token: str, mcp_clients: Dict[str, MCPClient]) -> Agent:
        """Create Nutritionist agent with meal and nutrition tools.
        
        Args:
            auth_token: JWT token for GraphQL authentication
            mcp_clients: Dictionary of MCP clients {server_name: client}
            
        Returns:
            Nutritionist Agent instance
        """
        tools = []
        
        # Load meal tools
        if "meal" in mcp_clients:
            try:
                client = mcp_clients["meal"]
                # Client already started, list tools
                meal_tools = client.list_tools_sync()
                tools.extend(meal_tools)
                logger.info(f"✅ Nutritionist loaded {len(meal_tools)} meal tools")
            except Exception as e:
                logger.error(f"❌ Meal tool loading failed: {e}")
        
        # Load progress tracking tools from nutritional-profile
        if "nutritional_profile" in mcp_clients:
            try:
                client = mcp_clients["nutritional_profile"]
                # Client already started, list tools
                profile_tools = client.list_tools_sync()
                # MCP tools already configured, add all
                tools.extend(profile_tools)
                logger.info(f"✅ Nutritionist loaded {len(profile_tools)} profile tools")
            except Exception as e:
                logger.error(f"❌ Progress tool loading failed: {e}", exc_info=True)
        
        system_prompt = """Sei il Nutrizionista di Nutrifit - Esperto in alimentazione e analisi nutrizionale.

COMPETENZE:
1. **Analisi pasti** (15 tools disponibili):
   - Foto → `analyze_meal_photo` (richiede photo_url, mealType)
   - Testo → `analyze_meal_text` (es: "pasta al pomodoro 200g")
   - Barcode → `analyze_meal_barcode` (codice prodotto)
   - Conferma → `confirm_meal_analysis` dopo review utente

2. **Storico e statistiche**:
   - `get_meal_history` → pasti recenti con nutrienti
   - `get_daily_summary` → totali giornata (date: YYYY-MM-DD)
   - `get_summary_range` → trend settimanali/mensili

3. **Progress tracking**:
   - `get_progress_score` → aderenza obiettivi (date: YYYY-MM-DD)
   - `record_progress` → log giornaliero peso/calorie
   - `forecast_weight` → previsione peso ML

PARAMETRI CRITICI:
- mealType: BREAKFAST|LUNCH|DINNER|SNACK
- date: Formato YYYY-MM-DD (es: 2025-11-21)
- group_by: DAY|WEEK|MONTH

WORKFLOW ANALISI PASTO (CRITICO):
1. User fornisce pasto (foto/testo/barcode)
2. Chiama analyze_meal_* → **SALVA meal_id dalla risposta**
3. Mostra analisi nutrizionale dettagliata
4. ⚠️ **NON FINIRE QUI** - Chiedi: "Confermi questo pasto?" 
5. **ATTENDI risposta user** (sì/conferma/ok/salva)
6. Se conferma → `confirm_meal_analysis(meal_id)` → Salva DB
7. Solo DOPO conferma puoi terminare

⚠️ IMPORTANTE CONFERMA:
- analyze_meal_* crea analisi TEMPORANEA (non salvata)
- DEVI aspettare conferma user e chiamare confirm_meal_analysis
- Se user dice "conferma"/"sì"/"ok"/"salva" → USA meal_id salvato
- NON perdere meal_id tra messaggi!
- Se meal_id perso → rianalizza pasto da capo

REGOLE GENERALI:
- Date YYYY-MM-DD, NO timestamp ISO
- Risposte dettagliate con macro (proteine, carbs, grassi)
- Suggerisci miglioramenti dieta se richiesto
- NON rispondere a domande su attività fisica (transfer a personal_trainer)
- ITALIANO naturale

ESEMPIO:
User: "cosa ho mangiato oggi?"
→ get_daily_summary(date="2025-11-21")
→ "Oggi: 1850 kcal, 3 pasti. Colazione: 450 kcal (avena, latte)..."
"""

        return Agent(
            name="nutrizionista",
            model=self.anthropic_model,
            tools=tools,
            system_prompt=system_prompt,
        )

    def _create_trainer_agent(self, auth_token: str, mcp_clients: Dict[str, MCPClient]) -> Agent:
        """Create Personal Trainer agent with activity tracking tools.
        
        Args:
            auth_token: JWT token for GraphQL authentication
            mcp_clients: Dictionary of MCP clients {server_name: client}
            
        Returns:
            Personal Trainer Agent instance
        """
        tools = []
        
        # Load activity tools
        if "activity" in mcp_clients:
            try:
                client = mcp_clients["activity"]
                # Client already started, list tools
                activity_tools = client.list_tools_sync()
                tools.extend(activity_tools)
                logger.info(f"✅ Personal Trainer loaded {len(activity_tools)} activity tools")
            except Exception as e:
                logger.error(f"❌ Activity tool loading failed: {e}")
        
        system_prompt = """Sei il Personal Trainer di Nutrifit - Esperto in attività fisica e salute.

COMPETENZE:
1. **Query dati attività** (5 tools disponibili):
   - `get_activity_entries` → dati minuto-per-minuto (steps, HR, calories)
   - `get_activity_sync_entries` → delta giornaliero sincronizzato
   - `aggregate_activity_range` → statistiche aggregate (group_by: DAY/WEEK/MONTH)

2. **Sincronizzazione dati**:
   - `sync_activity_events` → batch import da dispositivi (Apple Health, Google Fit)
   - `sync_health_totals` → snapshot giornaliero totali

PARAMETRI CRITICI:
- source: APPLE_HEALTH|GOOGLE_FIT|MANUAL
- group_by: DAY|WEEK|MONTH
- date: YYYY-MM-DD
- idempotency_key: OBBLIGATORIO per sync (genera UUID)

WORKFLOW SYNC:
1. User chiede import dati → usa `sync_activity_events` con idempotency_key
2. Conferma eventi sincronizzati
3. Query con `aggregate_activity_range` per statistiche

REGOLE:
- Date YYYY-MM-DD, NO timestamp ISO
- Sync operations SEMPRE con idempotency_key unico
- Source UPPERCASE: APPLE_HEALTH, GOOGLE_FIT, MANUAL
- Risposte con insights: "Ottimo! 10k passi = 500 kcal bruciate"
- NON rispondere a domande su alimentazione (transfer a nutrizionista)
- ITALIANO motivazionale

ESEMPIO:
User: "quanti passi ho fatto oggi?"
→ aggregate_activity_range(group_by="DAY", date="2025-11-21")
→ "💪 Oggi: 8.450 passi, 420 kcal bruciate. Obiettivo 10k passi: 85% completato!"
"""

        return Agent(
            name="personal_trainer",
            model=self.anthropic_model,
            tools=tools,
            system_prompt=system_prompt,
        )

    def get_swarm_for_user(self, user_id: str, auth_token: str) -> Swarm:
        """Get or create Swarm instance for user with MCP-loaded tools.
        
        Args:
            user_id: User identifier
            auth_token: JWT token for GraphQL authentication
            
        Returns:
            Swarm instance with 3 agents (router, nutritionist, trainer)
        """
        # Check if swarm already exists for this user
        if user_id in self.swarms:
            logger.info(f"♻️  Reusing existing Swarm for user {user_id}")
            return self.swarms[user_id]["swarm"]
        
        logger.info(f"🆕 Creating new Swarm for user {user_id}")
        
        # Create MCP clients for this user with their auth token
        if user_id not in self.user_mcp_clients:
            logger.info(f"🚀 Creating MCP clients for user {user_id} with auth token")
            self.user_mcp_clients[user_id] = self._create_user_mcp_clients(auth_token)
        
        mcp_clients = self.user_mcp_clients[user_id]
        
        if not mcp_clients:
            logger.error("❌ Failed to create MCP clients for user")
            raise RuntimeError("MCP clients creation failed")
        
        logger.info(f"✅ Using {len(mcp_clients)} MCP clients for user {user_id}")
        
        # Create agents with MCP tools (clients already started)
        nutritionist = self._create_nutritionist_agent(auth_token, mcp_clients)
        trainer = self._create_trainer_agent(auth_token, mcp_clients)
        router = self._create_router_agent(auth_token, mcp_clients)
        
        # Configure handoff agents for router
        router.handoff_agents = [nutritionist, trainer]
        
        # Create Swarm with correct API
        swarm = Swarm(
            nodes=[router, nutritionist, trainer],  # "nodes" not "agents"
            entry_point=router,                      # "entry_point" not "starting_agent"
            max_handoffs=20,
            max_iterations=20,
        )
        
        # Store swarm and clients
        self.swarms[user_id] = {
            "swarm": swarm,
            "mcp_clients": mcp_clients,
        }
        
        logger.info(f"✅ Swarm created for user {user_id} with {len(mcp_clients)} MCP servers")
        return swarm

    def cleanup_user_swarm(self, user_id: str) -> None:
        """Cleanup Swarm and MCP clients for user.
        
        Args:
            user_id: User identifier
        """
        if user_id not in self.swarms:
            return
        
        logger.info(f"🧹 Cleaning up Swarm for user {user_id}")
        
        # Stop user's MCP clients
        if user_id in self.user_mcp_clients:
            logger.info(f"🛑 Stopping MCP clients for user {user_id}")
            for server_name, client in self.user_mcp_clients[user_id].items():
                try:
                    client.stop()
                    logger.info(f"✅ Stopped {server_name} for user {user_id}")
                except Exception as e:
                    logger.warning(f"⚠️  Failed to stop {server_name}: {e}")
            del self.user_mcp_clients[user_id]
        
        # Remove from storage
        del self.swarms[user_id]
        logger.info(f"✅ Swarm cleaned up for user {user_id}")

    def get_stats(self) -> Dict[str, Any]:
        """Get agent manager statistics.
        
        Returns:
            Dictionary with manager stats
        """
        return {
            "active_swarms": len(self.swarms),
            "mcp_servers": {
                name: path.exists() 
                for name, path in self.mcp_servers.items()
            },
            "model": self.anthropic_model.model_id if hasattr(self.anthropic_model, "model_id") else "unknown",
        }


# Global instance
agent_manager = NutrifitAgentManager()
