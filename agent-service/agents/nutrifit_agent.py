"""Nutrifit Agent configuration with MCP tools and Swarm multi-agent."""

import os
import logging
from typing import Dict, Optional, List, Any
from datetime import datetime
from mcp import stdio_client, StdioServerParameters
from strands import Agent
from strands.models.anthropic import AnthropicModel
from strands.multiagent import Swarm
from strands.tools.mcp import MCPClient

# Setup structured logging for Swarm observability
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class NutrifitAgentManager:
    """Manages Nutrifit agent instances with MCP tools."""

    def __init__(self):
        # Store swarms per user (MCP clients and agents created per-user with their token)
        self.swarms: Dict[str, Dict] = {}  # {user_id: {"swarm": Swarm, "mcp_clients": {...}}}
        self._initialized = True  # Just a flag, actual initialization is per-user

        # Config from environment
        self.mcp_base_path = os.getenv("MCP_BASE_PATH", "/app/MCP")
        self.mcp_python_path = os.getenv("MCP_PYTHON_PATH", f"{self.mcp_base_path}/.venv/bin/python")
        self.graphql_endpoint = os.getenv("GRAPHQL_ENDPOINT", "http://nutrifit-backend:8080/graphql")
        self.rest_api_endpoint = os.getenv("REST_API_ENDPOINT", "http://nutrifit-backend:8080/api/v1")
        
        # Anthropic Model configuration
        anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        model_id = os.getenv("STRANDS_MODEL", "claude-sonnet-4-20250514")
        
        self.anthropic_model = AnthropicModel(
            client_args={"api_key": anthropic_api_key},
            max_tokens=4096,
            model_id=model_id,
            params={"temperature": 0.7},
        )

    def initialize_mcp_clients(self) -> None:
        """Initialize is now a no-op. MCP clients are created per-user with their auth token."""
        print("✅ Agent manager ready (MCP clients will be created per-user)")

    def shutdown_mcp_clients(self) -> None:
        """Shutdown all user swarms and MCP clients."""
        print("🛑 Shutting down all user swarms and MCP clients...")
        
        for user_id in list(self.swarms.keys()):
            self.cleanup_user_swarm(user_id)
        
        print("✅ All swarms and MCP clients shutdown")

    def _create_router_tools(self, auth_token: str) -> List[Any]:
        """Create HTTP tools for Router agent (onboarding & user management).
        
        Args:
            auth_token: JWT token for GraphQL authentication
            
        Returns:
            List of HTTP tool callables for Router
        """
        from tools.http_tool_adapter import create_graphql_tool
        
        tools = []
        
        # ===== USER MANAGEMENT & ONBOARDING =====
        tools.append(create_graphql_tool(
            name="check_user_exists",
            description="Verifica se l'utente autenticato esiste già nel database Nutrifit",
            query="""query CheckUserExists { user { exists } }""",
            graphql_endpoint=self.graphql_endpoint,
            auth_token=auth_token,
        ))
        
        tools.append(create_graphql_tool(
            name="authenticate_or_create_user",
            description="Crea un nuovo utente al primo login oppure restituisce profilo esistente. Idempotente, sicuro da chiamare sempre.",
            query="""mutation AuthenticateOrCreate {
                user { authenticate {
                    userId auth0Sub preferences { data } createdAt updatedAt lastAuthenticatedAt isActive
                } }
            }""",
            graphql_endpoint=self.graphql_endpoint,
            auth_token=auth_token,
        ))
        
        tools.append(create_graphql_tool(
            name="get_current_user",
            description="Ottieni il profilo dell'utente autenticato con preferenze e dati personali",
            query="""query { user { me { userId auth0Sub preferences { data } createdAt updatedAt lastAuthenticatedAt isActive } } }""",
            graphql_endpoint=self.graphql_endpoint,
            auth_token=auth_token,
        ))
        
        # ===== PROFILE SETUP (for onboarding) =====
        tools.append(create_graphql_tool(
            name="get_nutritional_profile",
            description="Ottieni profilo nutrizionale per verificare se utente l'ha già configurato",
            query="""query GetProfile($userId: String!) {
                nutritionalProfile { nutritionalProfile(userId: $userId) {
                    profileId userId goal caloriesTarget
                    userData { weight height age sex activityLevel }
                    bmr { value }
                    tdee { value activityLevel }
                    macroSplit { proteinG carbsG fatG }
                    createdAt updatedAt
                } }
            }""",
            graphql_endpoint=self.graphql_endpoint,
            auth_token=auth_token,
            variables_mapper=lambda p: {"userId": p.get("userId")}
        ))
        
        tools.append(create_graphql_tool(
            name="create_nutritional_profile",
            description="Crea il profilo nutrizionale con calcolo automatico di BMR, TDEE e target macro. Richiede: userId, userData (weight, height, age, sex, activityLevel), goal, initialWeight",
            query="""mutation CreateProfile($input: CreateProfileInput!) {
                nutritionalProfile { createNutritionalProfile(input: $input) {
                    profileId userId goal caloriesTarget
                    userData { weight height age sex activityLevel }
                    bmr { value }
                    tdee { value activityLevel }
                    macroSplit { proteinG carbsG fatG }
                    createdAt
                } }
            }""",
            graphql_endpoint=self.graphql_endpoint,
            auth_token=auth_token,
            variables_mapper=lambda p: {
                "input": {
                    "userId": p.get("userId"),
                    "userData": {
                        "weight": p.get("weight"),
                        "height": p.get("height"),
                        "age": p.get("age"),
                        "sex": p.get("sex"),
                        "activityLevel": p.get("activityLevel")
                    },
                    "goal": p.get("goal"),
                    "initialWeight": p.get("initialWeight"),
                    "initialDate": p.get("initialDate", None)
                }
            }
        ))
        
        return tools
    
    def _create_nutritionist_tools(self, auth_token: str) -> List[Any]:
        """Create tools for Nutritionist agent: meals, nutrition analysis, progress.
        
        Args:
            auth_token: JWT token for GraphQL authentication
            
        Returns:
            List of HTTP tool callables for Nutritionist
        """
        tools = []
        
        # ===== MEAL ANALYTICS =====
        tools.append(create_graphql_tool(
            name="get_meal_history",
            description="Recupera lo storico pasti dell'utente con dati nutrizionali dettagliati e ingredienti",
            query="""query GetMealHistory($userId: String!, $limit: Int, $startDate: String, $endDate: String) {
                meals { mealHistory(userId: $userId, limit: $limit, startDate: $startDate, endDate: $endDate) {
                    meals { 
                        id mealType timestamp dishName
                        totalCalories totalProtein totalCarbs totalFat totalFiber totalSugar
                        entries { name displayName quantityG calories protein carbs fat }
                        source confidence
                    }
                    totalCount hasMore
                } }
            }""",
            graphql_endpoint=self.graphql_endpoint,
            auth_token=auth_token,
            variables_mapper=lambda p: {
                "userId": p.get("userId"),
                "limit": p.get("limit", 20),
                "startDate": p.get("startDate"),
                "endDate": p.get("endDate")
            }
        ))
        
        tools.append(create_graphql_tool(
            name="get_daily_meal_summary",
            description="Ottieni il riepilogo giornaliero dei pasti per una data specifica",
            query="""query DailySummary($userId: String!, $date: String!) {
                meals { dailySummary(userId: $userId, date: $date) {
                    date totalCalories totalProtein totalCarbs totalFat mealCount
                } }
            }""",
            graphql_endpoint=self.graphql_endpoint,
            auth_token=auth_token,
            variables_mapper=lambda p: {"userId": p.get("userId"), "date": p.get("date")}
        ))
        
        # ===== NUTRITIONAL PROFILE & PROGRESS =====
        # Note: get/create_nutritional_profile are in Router for onboarding
        # Nutritionist only needs progress tracking and stats
        
        tools.append(create_graphql_tool(
            name="get_progress_statistics",
            description="Ottieni statistiche di progresso nutrizionale con adherence e trend peso",
            query="""query ProgressStats($userId: String!, $startDate: String!, $endDate: String!) {
                nutritionalProfile { progressStatistics(userId: $userId, startDate: $startDate, endDate: $endDate) {
                    startDate endDate weightDelta avgDailyCalories avgCaloriesBurned 
                    avgDeficit daysDeficitOnTrack daysMacrosOnTrack totalDays adherenceRate
                } }
            }""",
            graphql_endpoint=self.graphql_endpoint,
            auth_token=auth_token,
            variables_mapper=lambda p: {
                "userId": p.get("userId"),
                "startDate": p.get("startDate"),
                "endDate": p.get("endDate")
            }
        ))
        
        # ===== CRITICAL MEAL LOGGING TOOLS =====
        
        tools.append(create_graphql_tool(
            name="analyze_meal_photo",
            description="Analizza pasto da foto con AI (Vision + USDA enrichment). Crea meal PENDING da confermare con confirm_meal_analysis. Richiede: userId, photoUrl (da upload o URL esterno), mealType (BREAKFAST/LUNCH/DINNER/SNACK)",
            query="""mutation AnalyzeMealPhoto($input: AnalyzeMealPhotoInput!) {
                meals { analyzeMealPhoto(input: $input) {
                    ... on MealAnalysisSuccess {
                        meal {
                            id userId mealType timestamp dishName imageUrl
                            totalCalories totalProtein totalCarbs totalFat
                            entries { id name quantityG calories protein carbs fat }
                        }
                    }
                    ... on MealAnalysisError { message code }
                } }
            }""",
            graphql_endpoint=self.graphql_endpoint,
            auth_token=auth_token,
            variables_mapper=lambda p: {
                "input": {
                    "userId": p.get("userId"),
                    "photoUrl": p.get("photoUrl"),
                    "mealType": p.get("mealType")
                }
            }
        ))
        
        tools.append(create_graphql_tool(
            name="analyze_meal_text",
            description="Analizza pasto da descrizione testuale con AI. Crea meal PENDING da confermare. Richiede: userId, textDescription (es: 'pollo 150g con riso e verdure'), mealType",
            query="""mutation AnalyzeMealText($input: AnalyzeMealTextInput!) {
                meals { analyzeMealText(input: $input) {
                    ... on MealAnalysisSuccess {
                        meal {
                            id userId mealType timestamp dishName
                            totalCalories totalProtein totalCarbs totalFat
                            entries { id name quantityG calories protein carbs fat }
                        }
                    }
                    ... on MealAnalysisError { message code }
                } }
            }""",
            graphql_endpoint=self.graphql_endpoint,
            auth_token=auth_token,
            variables_mapper=lambda p: {
                "input": {
                    "userId": p.get("userId"),
                    "textDescription": p.get("textDescription"),
                    "mealType": p.get("mealType")
                }
            }
        ))
        
        tools.append(create_graphql_tool(
            name="confirm_meal_analysis",
            description="Conferma meal analizzato e salva. OBBLIGATORIO dopo analyze_meal_photo/text. Richiede: mealId (da analyze), userId, confirmedEntryIds (array IDs entries da mantenere, empty array = elimina tutto)",
            query="""mutation ConfirmMealAnalysis($input: ConfirmAnalysisInput!) {
                meals { confirmMealAnalysis(input: $input) {
                    ... on ConfirmAnalysisSuccess {
                        meal {
                            id totalCalories totalProtein totalCarbs totalFat
                            entries { id name quantityG calories protein carbs fat }
                        }
                    }
                    ... on ConfirmAnalysisError { message code }
                } }
            }""",
            graphql_endpoint=self.graphql_endpoint,
            auth_token=auth_token,
            variables_mapper=lambda p: {
                "input": {
                    "mealId": p.get("mealId"),
                    "userId": p.get("userId"),
                    "confirmedEntryIds": p.get("confirmedEntryIds", [])
                }
            }
        ))
        
        # ===== CRITICAL PROGRESS TRACKING =====
        
        tools.append(create_graphql_tool(
            name="record_progress",
            description="Registra progresso giornaliero (peso, calorie, macro). USA ogni volta che utente comunica nuovo peso. Richiede: userId, date (YYYY-MM-DD), weight (kg). Opzionali: caloriesConsumed",
            query="""mutation RecordProgress($input: RecordProgressInput!) {
                nutritionalProfile { recordProgress(input: $input) {
                    date weight consumedCalories consumedProteinG consumedCarbsG consumedFatG
                    caloriesBurnedBmr caloriesBurnedActive notes
                } }
            }""",
            graphql_endpoint=self.graphql_endpoint,
            auth_token=auth_token,
            variables_mapper=lambda p: {
                "input": {
                    "userId": p.get("userId"),
                    "date": p.get("date"),
                    "weight": p.get("weight"),
                    "caloriesConsumed": p.get("caloriesConsumed")
                }
            }
        ))
        
        return tools
    
    def _create_personal_trainer_tools(self, auth_token: str) -> List[Any]:
        """Create tools for Personal Trainer agent: activity tracking and sync.
        
        Args:
            auth_token: JWT token for GraphQL authentication
            
        Returns:
            List of HTTP tool callables for Personal Trainer
        """
        tools = []
        
        # ===== ACTIVITY TRACKING TOOLS =====
        
        tools.append(create_graphql_tool(
            name="get_activity_entries",
            description="Recupera dati minuto-per-minuto di attività fisica (passi, calorie, battito)",
            query="""query GetActivities($userId: String!, $limit: Int, $after: String) {
                activity { entries(userId: $userId, limit: $limit, after: $after) {
                    userId ts steps caloriesOut hrAvg source
                } }
            }""",
            graphql_endpoint=self.graphql_endpoint,
            auth_token=auth_token,
            variables_mapper=lambda p: {
                "userId": p.get("userId"),
                "limit": p.get("limit", 100),
                "after": p.get("after")
            }
        ))
        
        tools.append(create_graphql_tool(
            name="aggregate_activity_range",
            description="Aggrega attività per range con totale passi, calorie bruciate, minuti attivi e battito medio",
            query="""query AggregateActivity($userId: String!, $startDate: String!, $endDate: String!, $groupBy: GroupByPeriod) {
                activity { aggregateRange(userId: $userId, startDate: $startDate, endDate: $endDate, groupBy: $groupBy) {
                    periods { period startDate endDate totalSteps totalCaloriesOut totalActiveMinutes avgHeartRate }
                    total { period startDate endDate totalSteps totalCaloriesOut totalActiveMinutes avgHeartRate }
                } }
            }""",
            graphql_endpoint=self.graphql_endpoint,
            auth_token=auth_token,
            variables_mapper=lambda p: {
                "userId": p.get("userId"),
                "startDate": p.get("startDate"),
                "endDate": p.get("endDate"),
                "groupBy": p.get("groupBy", "DAY")
            }
        ))
        
        # ===== CRITICAL ACTIVITY SYNC =====
        
        tools.append(create_graphql_tool(
            name="sync_activity_events",
            description="Sincronizza eventi attività da HealthKit/GoogleFit (IDEMPOTENTE). Batch upload con deduplicazione. Richiede: userId, events (array con timestamp, steps, caloriesOut, hrAvg), source (APPLE_HEALTH/GOOGLE_FIT/MANUAL), idempotencyKey (opzionale, per retry sicuri)",
            query="""mutation SyncActivityEvents($input: [ActivityMinuteInput!]!, $idempotencyKey: String, $userId: String) {
                activity { syncActivityEvents(input: $input, idempotencyKey: $idempotencyKey, userId: $userId) {
                    accepted duplicates
                    rejected { index reason }
                    idempotencyKeyUsed
                } }
            }""",
            graphql_endpoint=self.graphql_endpoint,
            auth_token=auth_token,
            variables_mapper=lambda p: {
                "input": [
                    {
                        "ts": e.get("timestamp"),
                        "steps": e.get("steps", 0),
                        "caloriesOut": e.get("caloriesOut"),
                        "hrAvg": e.get("hrAvg"),
                        "source": p.get("source")
                    } for e in p.get("events", [])
                ],
                "idempotencyKey": p.get("idempotencyKey"),
                "userId": p.get("userId")
            }
        ))
        
        # ===== CROSS-DOMAIN READ-ONLY TOOLS (per calcoli calorico) =====
        
        tools.append(create_graphql_tool(
            name="get_nutritional_profile",
            description="Ottieni profilo nutrizionale per TDEE e target calorico (read-only)",
            query="""query GetProfile($userId: String!) {
                nutritionalProfile { nutritionalProfile(userId: $userId) {
                    profileId userId goal caloriesTarget
                    userData { weight height age sex activityLevel }
                    bmr { value formula }
                    tdee { value activityMultiplier }
                    macroSplit { proteinG carbsG fatG proteinPct carbsPct fatPct }
                    createdAt updatedAt
                } }
            }""",
            graphql_endpoint=self.graphql_endpoint,
            auth_token=auth_token,
            variables_mapper=lambda p: {"userId": p.get("userId")}
        ))
        
        tools.append(create_graphql_tool(
            name="get_daily_meal_summary",
            description="Riepilogo pasti giornaliero per bilancio calorico (read-only)",
            query="""query DailySummary($userId: String!, $date: String!) {
                meals { dailySummary(userId: $userId, date: $date) {
                    date totalCalories totalProtein totalCarbs totalFat mealCount
                } }
            }""",
            graphql_endpoint=self.graphql_endpoint,
            auth_token=auth_token,
            variables_mapper=lambda p: {"userId": p.get("userId"), "date": p.get("date")}
        ))
        
        return tools

    def _create_mcp_clients_for_user(self, auth_token: str) -> Dict[str, MCPClient]:
        """Create MCP clients with FastMCP stdio servers.
        
        Args:
            auth_token: JWT token to pass to MCP servers
            
        Returns:
            Dictionary of initialized MCP clients
        """
        mcp_clients = {}
        
        # User MCP
        mcp_clients["user"] = MCPClient(
            lambda: stdio_client(
                StdioServerParameters(
                    command=self.mcp_python_path,
                    args=[f"{self.mcp_base_path}/user-mcp/server_fastmcp.py"],
                    env={
                        "GRAPHQL_ENDPOINT": self.graphql_endpoint,
                        "AUTH0_TOKEN": auth_token,
                    },
                )
            ),
            prefix="user",
        )

        # Meal MCP
        mcp_clients["meal"] = MCPClient(
            lambda: stdio_client(
                StdioServerParameters(
                    command=self.mcp_python_path,
                    args=[f"{self.mcp_base_path}/meal-mcp/server_fastmcp.py"],
                    env={
                        "GRAPHQL_ENDPOINT": self.graphql_endpoint,
                        "REST_API_ENDPOINT": self.rest_api_endpoint,
                        "AUTH0_TOKEN": auth_token,
                    },
                )
            ),
            prefix="meal",
        )

        # Activity MCP
        mcp_clients["activity"] = MCPClient(
            lambda: stdio_client(
                StdioServerParameters(
                    command=self.mcp_python_path,
                    args=[f"{self.mcp_base_path}/activity-mcp/server_fastmcp.py"],
                    env={
                        "GRAPHQL_ENDPOINT": self.graphql_endpoint,
                        "AUTH0_TOKEN": auth_token,
                    },
                )
            ),
            prefix="activity",
        )

        # Nutritional Profile MCP
        mcp_clients["profile"] = MCPClient(
            lambda: stdio_client(
                StdioServerParameters(
                    command=self.mcp_python_path,
                    args=[f"{self.mcp_base_path}/nutritional-profile-mcp/server_fastmcp.py"],
                    env={
                        "GRAPHQL_ENDPOINT": self.graphql_endpoint,
                        "AUTH0_TOKEN": auth_token,
                    },
                )
            ),
            prefix="profile",
        )
        
        # Don't call __enter__() - let Strands manage the MCP client lifecycle
        print(f"✅ Created {len(mcp_clients)} MCP clients (will be initialized by Strands)")
        
        return mcp_clients

    def get_swarm_for_user(self, user_id: str, auth_token: str) -> Swarm:
        """Get or create swarm instance for user with specialized agents.

        Args:
            user_id: Auth0 user ID (sub)
            auth_token: JWT token for backend authentication (passed to MCP servers)

        Returns:
            Configured Swarm with Nutritionist and Personal Trainer agents
        """
        # Return cached swarm if exists
        if user_id in self.swarms:
            print(f"♻️ Reusing cached swarm for user {user_id}")
            return self.swarms[user_id]["swarm"]

        print(f"🆕 Creating new swarm for user {user_id}")
        
        # Create SEPARATE tool sets for each agent (Swarm pattern with Router)
        print("🔧 Loading specialized tools for each agent...")
        router_tools = self._create_router_tools(auth_token)
        nutritionist_tools = self._create_nutritionist_tools(auth_token)
        personal_trainer_tools = self._create_personal_trainer_tools(auth_token)
        print(f"✅ Router: {len(router_tools)} tools | Nutrizionista: {len(nutritionist_tools)} tools | Personal Trainer: {len(personal_trainer_tools)} tools")
        
        # Create Router Agent (entry point - handles onboarding and delegates)
        router = Agent(
            name="nutrifit_router",
            tools=router_tools,
            model=self.anthropic_model,
            system_prompt=f"""
Sei il ROUTER del team Nutrifit per utente {user_id}.

**RUOLO**: Entry point, onboarding, orchestrazione.

**TOOL TUO**:
• User: check_user_exists, authenticate_or_create_user, get_current_user
• Profile setup: get_nutritional_profile, create_nutritional_profile

**WORKFLOW ONBOARDING** (PRIORITÀ MASSIMA):
1. check_user_exists → verifica se user in DB
2. Se false: authenticate_or_create_user → crea user
3. get_nutritional_profile(userId) → verifica se ha profilo
4. Se null: create_nutritional_profile → setup completo
   Raccogli: peso, altezza, età, sesso, livello attività, obiettivo
5. Conferma setup completato

**HANDOFF STRATEGY** (DOPO onboarding):
→ handoff_to_agent("nutrizionista") SE richiesta su:
  - Logging pasti (foto, testo, barcode)
  - Analisi nutrizionale, calorie intake
  - Progressi peso, statistiche adherence
  - Consigli alimentazione

→ handoff_to_agent("personal_trainer") SE richiesta su:
  - Attività fisica, passi, calorie bruciate
  - Sync HealthKit/GoogleFit
  - Workout, allenamenti
  - Statistiche fitness

**DELEGAZIONE OBBLIGATORIA**: Dopo onboarding, handoff SEMPRE agli specialisti.
NON rispondere direttamente su pasti/attività - sei solo orchestratore.

Rispondi in italiano. Onboarding first, poi delega.
            """,
        )
        
        # Create Nutritionist Agent (focuses on meals and nutrition)
        nutritionist = Agent(
            name="nutrizionista",
            tools=nutritionist_tools,
            model=self.anthropic_model,
            system_prompt=f"""
Sei il NUTRIZIONISTA del team Nutrifit per utente {user_id}.

**SPECIALIZZAZIONE**: Nutrizione, pasti, profilo, peso, obiettivi calorici.

**TOOL TUO**:
• User: check_user_exists, authenticate_or_create_user, get_current_user
• Meal logging: analyze_meal_photo, analyze_meal_text, confirm_meal_analysis
• Analytics: get_meal_history, get_daily_meal_summary
• Profile: get/create_nutritional_profile, record_progress, get_progress_statistics

**WORKFLOW LOGGING PASTO**:
1. analyze_meal_photo/text → meal PENDING
2. Mostra entries rilevate, chiedi conferma utente
3. confirm_meal_analysis(mealId, confirmedEntryIds) → CONFIRMED

**HANDOFF STRATEGY**:
→ handoff_to_agent("personal_trainer") SE richiesta su:
  - Attività fisica, workout, calorie bruciate
  - Sync HealthKit/GoogleFit
  
→ handoff_to_agent("nutrifit_router") SE utente nuovo SENZA profilo
  - Router gestisce onboarding completo
  
**NON HANDOFF** (gestisci tu):
- Logging pasti (analyze, confirm)
- Analisi nutrizionale, macro
- Peso, progressi (record_progress)
- Statistiche adherence

Rispondi SEMPRE in italiano. Usa tool prima di rispondere.
            """,
        )

        # Create Personal Trainer Agent (focuses on activities and fitness)
        personal_trainer = Agent(
            name="personal_trainer",
            tools=personal_trainer_tools,
            model=self.anthropic_model,
            system_prompt=f"""
Sei il PERSONAL TRAINER del team Nutrifit per utente {user_id}.

**SPECIALIZZAZIONE**: Attività fisica, workout, consumo calorico, sync HealthKit/GoogleFit.

**TOOL TUO**:
• Activity: get_activity_entries, aggregate_activity_range, sync_activity_events
• Cross-domain (read-only): get_nutritional_profile (TDEE), get_daily_meal_summary (intake)

**WORKFLOW SYNC ATTIVITÀ**:
1. sync_activity_events(userId, events[], source, idempotencyKey) → batch upload
2. Idempotente: stesso idempotencyKey = skip duplicati
3. aggregate_activity_range per statistiche periodo

**HANDOFF STRATEGY**:
→ handoff_to_agent("nutrizionista") SE richiesta su:
  - Pasti, logging, calorie intake
  - Peso, progressi nutrizionali
  - Macro (proteine, carbs, grassi)

→ handoff_to_agent("nutrifit_router") SE utente nuovo SENZA profilo
  - Router gestisce onboarding
  
**NON HANDOFF** (gestisci tu):
- Passi, distanza, workout
- Calorie bruciate attività
- Sync dispositivi fitness
- Bilancio calorico (intake - burn)

**BILANCIO CALORICO**:
Deficit = meal_summary.totalCalories - (TDEE + activity_calories)

Rispondi SEMPRE in italiano. Usa tool prima di rispondere. Motiva l'utente!
            """,
        )

        # Create Swarm with Router as entry point (orchestrator pattern)
        swarm = Swarm(
            nodes=[router, nutritionist, personal_trainer],
            entry_point=router,  # Router handles onboarding and delegates
            max_handoffs=20,  # Increased: complex workflows need multiple handoffs
            max_iterations=30,  # Increased: meal analysis + confirm + handoffs need iterations
            execution_timeout=300.0,  # 5 minutes total (reasonable for complex queries)
            node_timeout=60.0,  # 1 minute per agent (was 120s, too high)
            repetitive_handoff_detection_window=6,  # Detect ping-pong in last 6 handoffs
            repetitive_handoff_min_unique_agents=2,  # Require at least 2 unique agents
        )

        # Cache swarm for reuse (no MCP clients in fallback mode)
        self.swarms[user_id] = {
            "swarm": swarm,
            "mcp_clients": {},  # Empty in fallback mode
            "created_at": __import__("datetime").datetime.now().isoformat(),
            "handoff_count": 0,
            "iteration_count": 0,
        }
        
        # Structured logging for observability
        logger.info(
            "swarm_created",
            extra={
                "user_id": user_id,
                "agents": ["nutrifit_router", "nutrizionista", "personal_trainer"],
                "entry_point": "nutrifit_router",
                "router_tools": len(router_tools),
                "nutritionist_tools": len(nutritionist_tools),
                "trainer_tools": len(personal_trainer_tools),
                "max_handoffs": 20,
                "max_iterations": 30,
            }
        )
        print(f"✅ Swarm created for user {user_id}: router ({len(router_tools)} tools) → nutrizionista ({len(nutritionist_tools)} tools) + personal_trainer ({len(personal_trainer_tools)} tools)")

        return swarm

    def cleanup_user_swarm(self, user_id: str) -> None:
        """Cleanup swarm and MCP clients for a user."""
        if user_id in self.swarms:
            # Strands manages MCP client lifecycle, just remove from cache
            del self.swarms[user_id]
            print(f"🗑️ Removed swarm for user {user_id}")

    def get_stats(self) -> Dict[str, any]:
        """Get swarm manager statistics."""
        return {
            "initialized": self._initialized,
            "active_swarms": len(self.swarms),
            "active_users": list(self.swarms.keys()),
            "agents_per_swarm": ["nutrifit_router", "nutrizionista", "personal_trainer"],
        }


# Global singleton
agent_manager = NutrifitAgentManager()
