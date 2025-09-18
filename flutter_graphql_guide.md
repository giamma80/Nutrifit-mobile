## 13. Deployment & Production

### Build Configurations

Crea `android/app/src/main/kotlin/MainActivity.kt`:

```kotlin
package com.yourcompany.healthtracker

import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugins.GeneratedPluginRegistrant

class MainActivity: FlutterActivity() {
    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        GeneratedPluginRegistrant.registerWith(flutterEngine)
    }
}
```

### CI/CD Pipeline Example (.github/workflows/build.yml)

```yaml
name: Build and Test

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Flutter
        uses: subosito/flutter-action@v2
        with:
          flutter-version: '3.16.0'
          
      - name: Get dependencies
        run: flutter pub get
        
      - name: Generate code
        run: flutter packages pub run build_runner build --delete-conflicting-outputs
        
      - name: Run tests
        run: flutter test
        
      - name: Run integration tests
        run: flutter test integration_test/

  build_android:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Flutter
        uses: subosito/flutter-action@v2
        with:
          flutter-version: '3.16.0'
          
      - name: Build APK
        run: flutter build apk --release
        
      - name: Upload APK
        uses: actions/upload-artifact@v3
        with:
          name: release-apk
          path: build/app/outputs/flutter-apk/app-release.apk

  build_ios:
    needs: test
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Flutter
        uses: subosito/flutter-action@v2
        with:
          flutter-version: '3.16.0'
          
      - name: Build iOS
        run: flutter build ios --release --no-codesign
```

### Performance Monitoring

Crea `lib/services/monitoring/performance_service.dart`:

```dart
import 'package:flutter/foundation.dart';

class PerformanceService {
  static final PerformanceService _instance = PerformanceService._internal();
  factory PerformanceService() => _instance;
  PerformanceService._internal();

  // Track GraphQL query performance
  void trackQueryPerformance(String queryName, Duration duration) {
    if (kDebugMode) {
      debugPrint('GraphQL Query "$queryName" took ${duration.inMilliseconds}ms');
    }
    
    // Send to analytics service in production
    if (kReleaseMode) {
      _sendToAnalytics('graphql_query_performance', {
        'query_name': queryName,
        'duration_ms': duration.inMilliseconds,
      });
    }
  }

  // Track health sync performance
  void trackSyncPerformance(int metricsCount, Duration duration, bool success) {
    final data = {
      'metrics_count': metricsCount,
      'duration_ms': duration.inMilliseconds,
      'success': success,
    };
    
    if (kDebugMode) {
      debugPrint('Health sync: $data');
    }
    
    if (kReleaseMode) {
      _sendToAnalytics('health_sync_performance', data);
    }
  }

  void _sendToAnalytics(String event, Map<String, dynamic> data) {
    // Implement analytics tracking (Firebase, Mixpanel, etc.)
  }
}
```

## 14. Security Considerations

### Token Security

```dart
// lib/services/auth/token_service.dart
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:crypto/crypto.dart';

class TokenService {
  static const _storage = FlutterSecureStorage(
    aOptions: AndroidOptions(
      encryptedSharedPreferences: true,
    ),
    iOptions: IOSOptions(
      accessibility: IOSAccessibility.first_unlock_this_device,
    ),
  );

  static Future<void> storeTokenSecurely(String token) async {
    // Hash the token for additional security
    final hashedToken = sha256.convert(token.codeUnits).toString();
    
    await _storage.write(
      key: 'auth_token_hash',
      value: hashedToken,
    );
    
    await _storage.write(
      key: 'auth_token',
      value: token,
    );
  }

  static Future<String?> getTokenSecurely() async {
    return await _storage.read(key: 'auth_token');
  }

  static Future<void> clearTokens() async {
    await _storage.deleteAll();
  }
}
```

### Health Data Privacy

```dart
// lib/services/privacy/data_privacy_service.dart
class DataPrivacyService {
  // Anonymize health data before sending to server
  static Map<String, dynamic> anonymizeHealthData(Map<String, dynamic> data) {
    final anonymized = Map<String, dynamic>.from(data);
    
    // Remove or hash personally identifiable information
    anonymized.remove('deviceId');
    anonymized.remove('userId'); // Will be added by server from JWT
    
    // Add privacy flags
    anonymized['anonymized'] = true;
    anonymized['privacyLevel'] = 'high';
    
    return anonymized;
  }

  // Check data sharing permissions
  static bool canShareHealthData(PrivacyLevel userPrivacy, String dataType) {
    switch (userPrivacy) {
      case PrivacyLevel.public:
        return true;
      case PrivacyLevel.friends:
        return ['steps', 'workouts'].contains(dataType);
      case PrivacyLevel.private:
        return false;
    }
  }
}
```

## 15. Error Handling & Logging

### Global Error Handler

```dart
// lib/core/errors/global_error_handler.dart
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

class GlobalErrorHandler {
  static void initialize() {
    // Handle Flutter framework errors
    FlutterError.onError = (FlutterErrorDetails details) {
      FlutterError.presentError(details);
      
      if (kReleaseMode) {
        // Send to crash reporting service
        _reportError(details.exception, details.stack);
      }
    };

    // Handle other errors
    PlatformDispatcher.instance.onError = (error, stack) {
      if (kReleaseMode) {
        _reportError(error, stack);
      }
      return true;
    };
  }

  static void _reportError(Object error, StackTrace? stack) {
    // Send to Firebase Crashlytics, Sentry, etc.
    debugPrint('Error: $error\nStack: $stack');
  }

  // GraphQL specific error handling
  static String getReadableErrorMessage(dynamic error) {
    if (error.toString().contains('UNAUTHENTICATED')) {
      return 'Please log in again to continue';
    } else if (error.toString().contains('NETWORK_ERROR')) {
      return 'Check your internet connection and try again';
    } else if (error.toString().contains('TIMEOUT')) {
      return 'Request timed out. Please try again';
    } else {
      return 'Something went wrong. Please try again';
    }
  }
}
```

### Health Data Specific Errors

```dart
// lib/core/errors/health_exceptions.dart
class HealthDataException implements Exception {
  final String message;
  final HealthErrorType type;
  
  const HealthDataException(this.message, this.type);
  
  @override
  String toString() => 'HealthDataException: $message';
}

enum HealthErrorType {
  permissionDenied,
  dataNotAvailable,
  syncFailed,
  platformNotSupported,
  rateLimitExceeded,
}

class HealthExceptionHandler {
  static String getReadableMessage(HealthDataException exception) {
    switch (exception.type) {
      case HealthErrorType.permissionDenied:
        return 'Health data access was denied. Please enable permissions in Settings.';
      case HealthErrorType.dataNotAvailable:
        return 'No health data is available for the selected period.';
      case HealthErrorType.syncFailed:
        return 'Failed to sync health data. Will retry automatically.';
      case HealthErrorType.platformNotSupported:
        return 'Health data is not supported on this device.';
      case HealthErrorType.rateLimitExceeded:
        return 'Too many requests. Please wait a moment and try again.';
    }
  }
}
```

## 16. Performance Optimization

### Lazy Loading & Pagination

```dart
// lib/presentation/providers/paginated_health_provider.dart
import 'package:flutter_riverpod/flutter_riverpod.dart';

class PaginatedHealthData {
  final List<DailySummary> items;
  final bool hasMore;
  final bool isLoading;
  final String? error;

  const PaginatedHealthData({
    this.items = const [],
    this.hasMore = true,
    this.isLoading = false,
    this.error,
  });

  PaginatedHealthData copyWith({
    List<DailySummary>? items,
    bool? hasMore,
    bool? isLoading,
    String? error,
  }) {
    return PaginatedHealthData(
      items: items ?? this.items,
      hasMore: hasMore ?? this.hasMore,
      isLoading: isLoading ?? this.isLoading,
      error: error ?? this.error,
    );
  }
}

class PaginatedHealthNotifier extends StateNotifier<PaginatedHealthData> {
  PaginatedHealthNotifier() : super(const PaginatedHealthData()) {
    loadFirstPage();
  }

  static const int _pageSize = 20;
  int _currentPage = 0;

  Future<void> loadFirstPage() async {
    state = state.copyWith(isLoading: true, error: null);
    
    try {
      final data = await _fetchHealthData(page: 0, pageSize: _pageSize);
      
      state = state.copyWith(
        items: data,
        hasMore: data.length == _pageSize,
        isLoading: false,
      );
      
      _currentPage = 0;
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
    }
  }

  Future<void> loadNextPage() async {
    if (state.isLoading || !state.hasMore) return;
    
    state = state.copyWith(isLoading: true);
    
    try {
      final newData = await _fetchHealthData(
        page: _currentPage + 1,
        pageSize: _pageSize,
      );
      
      final allItems = [...state.items, ...newData];
      
      state = state.copyWith(
        items: allItems,
        hasMore: newData.length == _pageSize,
        isLoading: false,
      );
      
      _currentPage++;
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
    }
  }

  Future<List<DailySummary>> _fetchHealthData({
    required int page,
    required int pageSize,
  }) async {
    // Implement GraphQL pagination query
    return [];
  }
}

final paginatedHealthProvider = StateNotifierProvider<PaginatedHealthNotifier, PaginatedHealthData>((ref) {
  return PaginatedHealthNotifier();
});
```

### Memory Management

```dart
// lib/core/utils/memory_utils.dart
class MemoryUtils {
  // Clean up old cached health data
  static void cleanupOldHealthData() {
    final threshold = DateTime.now().subtract(const Duration(days: 90));
    
    // Remove data older than 90 days from local cache
    // Implementation would clear Hive boxes, etc.
  }

  // Optimize image loading for user avatars
  static Widget optimizedNetworkImage(String url, {double? width, double? height}) {
    return Image.network(
      url,
      width: width,
      height: height,
      cacheWidth: width?.toInt(),
      cacheHeight: height?.toInt(),
      errorBuilder: (context, error, stackTrace) {
        return Container(
          width: width,
          height: height,
          color: Colors.grey[300],
          child: Icon(Icons.person, color: Colors.grey[600]),
        );
      },
    );
  }
}
```

## 17. Accessibility & Internationalization

### Accessibility

```dart
// lib/core/accessibility/accessibility_utils.dart
class AccessibilityUtils {
  // Semantic labels for health metrics
  static String getHealthMetricSemantics(String metric, dynamic value) {
    switch (metric.toLowerCase()) {
      case 'steps':
        return 'Steps taken today: $value';
      case 'calories':
        return 'Calories burned today: $value';
      case 'distance':
        return 'Distance traveled today: $value kilometers';
      case 'heartrate':
        return 'Current heart rate: $value beats per minute';
      default:
        return '$metric: $value';
    }
  }

  // High contrast mode support
  static Color getAccessibleColor(BuildContext context, Color defaultColor) {
    final mediaQuery = MediaQuery.of(context);
    if (mediaQuery.highContrast) {
      return defaultColor == Colors.red ? Colors.red.shade800 : defaultColor;
    }
    return defaultColor;
  }
}
```

### Internationalization Setup

```dart
// lib/l10n/app_localizations.dart
import 'package:flutter/material.dart';

class AppLocalizations {
  final Locale locale;
  
  AppLocalizations(this.locale);
  
  static AppLocalizations of(BuildContext context) {
    return Localizations.of<AppLocalizations>(context, AppLocalizations)!;
  }

  // Health metrics
  String get steps => locale.languageCode == 'it' ? 'Passi' : 'Steps';
  String get calories => locale.languageCode == 'it' ? 'Calorie' : 'Calories';
  String get distance => locale.languageCode == 'it' ? 'Distanza' : 'Distance';
  String get heartRate => locale.languageCode == 'it' ? 'Frequenza Cardiaca' : 'Heart Rate';
  
  // Actions
  String get sync => locale.languageCode == 'it' ? 'Sincronizza' : 'Sync';
  String get login => locale.languageCode == 'it' ? 'Accedi' : 'Login';
  String get logout => locale.languageCode == 'it' ? 'Esci' : 'Logout';
  
  // Error messages
  String get connectionError => locale.languageCode == 'it' 
    ? 'Errore di connessione. Controlla la tua connessione internet.'
    : 'Connection error. Check your internet connection.';
}
```

## 18. Next Steps & Scaling

### Features da Aggiungere

1. **Real-time Notifications**
   - Achievement notifications
   - Goal reminders
   - Sync status updates

2. **Social Features**
   - Friends/family connections
   - Challenges and competitions
   - Data sharing with permission

3. **Advanced Analytics**
   - Trend analysis with ML
   - Personalized insights
   - Health score calculations

4. **Integration Expansion**
   - Wearable devices (Fitbit, Garmin, etc.)
   - Medical devices (blood pressure monitors)
   - Third-party fitness apps

### Architectural Improvements

```dart
// Future: Repository Pattern Enhancement
abstract class HealthRepository {
  Future<Result<List<HealthMetric>, HealthException>> getHealthData({
    required DateRange dateRange,
    List<HealthDataType>? types,
  });
  
  Future<Result<bool, HealthException>> syncToServer(List<HealthMetric> metrics);
  
  Stream<HealthMetric> watchRealTimeData();
}

// Future: Use Case Layer Enhancement
class SyncHealthDataUseCase {
  final HealthRepository _healthRepo;
  final UserRepository _userRepo;
  final AnalyticsRepository _analyticsRepo;
  
  SyncHealthDataUseCase(this._healthRepo, this._userRepo, this._analyticsRepo);
  
  Future<Result<SyncResult, AppException>> execute(SyncRequest request) async {
    // Complex business logic with multiple repositories
  }
}
```

### Performance Monitoring

```dart
// lib/services/monitoring/app_monitoring.dart
class AppMonitoring {
  static void trackScreenView(String screenName) {
    // Track user navigation patterns
  }
  
  static void trackFeatureUsage(String feature, Map<String, dynamic> properties) {
    // Track which features are most used
  }
  
  static void trackHealthDataVolume(int metricsCount, String source) {
    // Monitor health data processing volume
  }
}
```

## Conclusione

Questa architettura fornisce una **base solida e scalabile** per la tua app Flutter con:

✅ **Integrazione completa**: Auth0 + GraphQL + HealthKit/GoogleFit
✅ **Architettura pulita**: Separation of concerns, testabilità
✅ **Team-friendly**: Struttura chiara per sviluppatori junior  
✅ **Production-ready**: Error handling, security, performance
✅ **Scalabile**: Facile aggiungere nuove feature e piattaforme

### Quick Start Commands

```bash
# 1. Clone e setup
flutter create health_tracker_app
cd health_tracker_app

# 2. Setup dependencies (usa il pubspec.yaml della guida)
flutter pub get

# 3. Crea la struttura directory
mkdir -p lib/{config,core,data,domain,graphql,presentation,services}

# 4. Genera il codice
flutter packages pub run build_runner build

# 5. Run
flutter run
```

La struttura è **modulare** e permette al team di lavorare su diverse parti senza conflitti. Ogni servizio è **testabile** e **sostituibile**.

**Pro tip**: Inizia con le funzionalità core (auth + basic health data) e aggiungi feature incrementalmente! 🚀## 7. Routing e Navigation

### App Router Configuration

Crea `lib/config/routes.dart`:

```dart
import 'package:go_router/go_router.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../presentation/providers/auth_provider.dart';
import '../presentation/screens/auth/login_screen.dart';
import '../presentation/screens/auth/register_screen.dart';
import '../presentation/screens/auth/onboarding_screen.dart';
import '../presentation/screens/health/dashboard_screen.dart';
import '../presentation/screens/health/metrics_screen.dart';
import '../presentation/screens/health/trends_screen.dart';
import '../presentation/screens/health/sync_screen.dart';
import '../presentation/screens/profile/profile_screen.dart';
import '../presentation/screens/profile/settings_screen.dart';
import '../presentation/screens/common/splash_screen.dart';

final routerProvider = Provider<GoRouter>((ref) {
  final authState = ref.watch(authProvider);
  
  return GoRouter(
    initialLocation: '/',
    redirect: (context, state) {
      final isAuthenticated = authState.status == AuthStatus.authenticated;
      final isOnAuthRoute = ['/login', '/register', '/onboarding'].contains(state.location);
      
      // If not authenticated and not on auth route, go to login
      if (!isAuthenticated && !isOnAuthRoute) {
        return '/login';
      }
      
      // If authenticated and on auth route, go to dashboard
      if (isAuthenticated && isOnAuthRoute) {
        return '/dashboard';
      }
      
      return null; // No redirect needed
    },
    routes: [
      // Splash/Loading
      GoRoute(
        path: '/',
        builder: (context, state) => const SplashScreen(),
      ),
      
      // Authentication routes
      GoRoute(
        path: '/login',
        builder: (context, state) => const LoginScreen(),
      ),
      GoRoute(
        path: '/register',
        builder: (context, state) => const RegisterScreen(),
      ),
      GoRoute(
        path: '/onboarding',
        builder: (context, state) => const OnboardingScreen(),
      ),
      
      // Main app routes (authenticated)
      ShellRoute(
        builder: (context, state, child) => MainNavigationShell(child: child),
        routes: [
          GoRoute(
            path: '/dashboard',
            builder: (context, state) => const DashboardScreen(),
            routes: [
              GoRoute(
                path: 'metrics',
                builder: (context, state) => const MetricsScreen(),
              ),
              GoRoute(
                path: 'trends',
                builder: (context, state) => const TrendsScreen(),
              ),
              GoRoute(
                path: 'sync',
                builder: (context, state) => const SyncScreen(),
              ),
            ],
          ),
          GoRoute(
            path: '/profile',
            builder: (context, state) => const ProfileScreen(),
            routes: [
              GoRoute(
                path: 'settings',
                builder: (context, state) => const SettingsScreen(),
              ),
            ],
          ),
        ],
      ),
    ],
  );
});

// Main navigation shell with bottom navigation
class MainNavigationShell extends ConsumerWidget {
  final Widget child;
  
  const MainNavigationShell({Key? key, required this.child}) : super(key: key);

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Scaffold(
      body: child,
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: _getCurrentIndex(context),
        onTap: (index) => _onTabTapped(context, index),
        items: const [
          BottomNavigationBarItem(
            icon: Icon(Icons.dashboard),
            label: 'Dashboard',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.person),
            label: 'Profile',
          ),
        ],
      ),
    );
  }

  int _getCurrentIndex(BuildContext context) {
    final location = GoRouterState.of(context).location;
    if (location.startsWith('/dashboard')) return 0;
    if (location.startsWith('/profile')) return 1;
    return 0;
  }

  void _onTabTapped(BuildContext context, int index) {
    switch (index) {
      case 0:
        context.go('/dashboard');
        break;
      case 1:
        context.go('/profile');
        break;
    }
  }
}
```

## 8. Data Models

### Core Models

Crea `lib/data/models/auth/auth_user.dart`:

```dart
import 'package:freezed_annotation/freezed_annotation.dart';

part 'auth_user.freezed.dart';
part 'auth_user.g.dart';

@freezed
class AuthUser with _$AuthUser {
  const factory AuthUser({
    required String id,
    required String email,
    required String name,
    String? avatar,
    HealthProfile? healthProfile,
    required DateTime createdAt,
  }) = _AuthUser;

  factory AuthUser.fromJson(Map<String, dynamic> json) => _$AuthUserFromJson(json);
}

@freezed
class HealthProfile with _$HealthProfile {
  const factory HealthProfile({
    required String id,
    required String userId,
    required HealthGoals goals,
    required UserPreferences preferences,
    DateTime? lastSyncAt,
  }) = _HealthProfile;

  factory HealthProfile.fromJson(Map<String, dynamic> json) => _$HealthProfileFromJson(json);
}

@freezed
class HealthGoals with _$HealthGoals {
  const factory HealthGoals({
    @Default(10000) int dailySteps,
    @Default(2000) int dailyCalories,
    @Default(150) int weeklyActiveMinutes,
    @Default(3) int weeklyWorkouts,
  }) = _HealthGoals;

  factory HealthGoals.fromJson(Map<String, dynamic> json) => _$HealthGoalsFromJson(json);
}

@freezed
class UserPreferences with _$UserPreferences {
  const factory UserPreferences({
    @Default(UnitSystem.metric) UnitSystem units,
    required NotificationSettings notifications,
    @Default(SyncFrequency.hourly) SyncFrequency syncFrequency,
    @Default(PrivacyLevel.private) PrivacyLevel privacyLevel,
  }) = _UserPreferences;

  factory UserPreferences.fromJson(Map<String, dynamic> json) => _$UserPreferencesFromJson(json);
}

enum UnitSystem { metric, imperial }
enum SyncFrequency { realTime, hourly, daily }
enum PrivacyLevel { public, friends, private }
```

Crea `lib/data/models/health/health_metric.dart`:

```dart
import 'package:freezed_annotation/freezed_annotation.dart';
import 'package:health/health.dart';

part 'health_metric.freezed.dart';
part 'health_metric.g.dart';

@freezed
class HealthMetric with _$HealthMetric {
  const factory HealthMetric({
    required HealthDataType type,
    required dynamic value,
    required DateTime timestamp,
    required String unit,
    String? source,
  }) = _HealthMetric;

  factory HealthMetric.fromJson(Map<String, dynamic> json) => _$HealthMetricFromJson(json);
  
  factory HealthMetric.fromHealthData(HealthDataPoint healthData) {
    return HealthMetric(
      type: healthData.type,
      value: healthData.value,
      timestamp: healthData.dateFrom,
      unit: healthData.unit.name,
      source: healthData.sourceName,
    );
  }
}

@freezed
class DailySummary with _$DailySummary {
  const factory DailySummary({
    required DateTime date,
    @Default(0) int steps,
    @Default(0.0) double caloriesBurned,
    @Default(0.0) double distance,
    @Default(0) int activeMinutes,
    @Default([]) List<WorkoutSummary> workouts,
    HeartRateData? heartRate,
  }) = _DailySummary;

  factory DailySummary.fromJson(Map<String, dynamic> json) => _$DailySummaryFromJson(json);
  
  factory DailySummary.fromMap(Map<String, dynamic> map) {
    return DailySummary(
      date: DateTime.parse(map['date'] ?? DateTime.now().toIso8601String()),
      steps: map['steps'] ?? 0,
      caloriesBurned: (map['calories'] ?? 0.0).toDouble(),
      distance: (map['distance'] ?? 0.0).toDouble(),
      activeMinutes: map['activeMinutes'] ?? 0,
    );
  }
}

@freezed
class WorkoutSummary with _$WorkoutSummary {
  const factory WorkoutSummary({
    required String id,
    required WorkoutType type,
    required int duration, // minutes
    required double caloriesBurned,
    required DateTime startTime,
    required DateTime endTime,
  }) = _WorkoutSummary;

  factory WorkoutSummary.fromJson(Map<String, dynamic> json) => _$WorkoutSummaryFromJson(json);
}

@freezed
class HeartRateData with _$HeartRateData {
  const factory HeartRateData({
    int? average,
    int? minimum,
    int? maximum,
    int? restingRate,
  }) = _HeartRateData;

  factory HeartRateData.fromJson(Map<String, dynamic> json) => _$HeartRateDataFromJson(json);
}

enum WorkoutType {
  running,
  walking,
  cycling,
  swimming,
  strengthTraining,
  yoga,
  other,
}
```

## 9. Main App Setup

### App Root

Crea `lib/app.dart`:

```dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:graphql_flutter/graphql_flutter.dart';
import 'config/routes.dart';
import 'config/theme.dart';
import 'services/auth/auth0_service.dart';
import 'services/graphql/graphql_service.dart';

class HealthApp extends ConsumerStatefulWidget {
  const HealthApp({Key? key}) : super(key: key);

  @override
  ConsumerState<HealthApp> createState() => _HealthAppState();
}

class _HealthAppState extends ConsumerState<HealthApp> {
  @override
  void initState() {
    super.initState();
    _initializeServices();
  }

  void _initializeServices() {
    // Initialize Auth0
    Auth0Service().initialize();
  }

  @override
  Widget build(BuildContext context) {
    final router = ref.watch(routerProvider);
    
    return GraphQLProvider(
      client: ValueNotifier(GraphQLService().client),
      child: MaterialApp.router(
        title: 'Health Tracker',
        theme: AppTheme.lightTheme,
        darkTheme: AppTheme.darkTheme,
        themeMode: ThemeMode.system,
        routerConfig: router,
        debugShowCheckedModeBanner: false,
      ),
    );
  }
}
```

### Main Entry Point

Attualizze `lib/main.dart`:

```dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:hive_flutter/hive_flutter.dart';
import 'app.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  
  // Initialize Hive for GraphQL caching
  await initHiveForFlutter();
  
  // Initialize local storage
  await Hive.initFlutter();
  
  runApp(
    const ProviderScope(
      child: HealthApp(),
    ),
  );
}
```

## 10. Build & Development Workflow

### Code Generation Commands

```bash
# Generate GraphQL code
flutter packages pub run build_runner build

# Watch for changes during development
flutter packages pub run build_runner watch

# Clean and regenerate
flutter packages pub run build_runner build --delete-conflicting-outputs

# Generate Freezed models
flutter packages pub run build_runner build --build-filter="lib/data/models/**"
```

### Development Scripts

Crea `scripts/generate.sh`:

```bash
#!/bin/bash
echo "🔄 Generating code..."

echo "📱 Generating GraphQL code..."
flutter packages pub run build_runner build --build-filter="lib/graphql/**"

echo "🏗️ Generating data models..."
flutter packages pub run build_runner build --build-filter="lib/data/models/**"

echo "✅ Code generation completed!"
```

### Environment Setup

Crea `.env.example`:

```
# GraphQL
GRAPHQL_ENDPOINT_DEV=http://localhost:4000/graphql
GRAPHQL_ENDPOINT_STAGING=https://staging-api.yourapp.com/graphql
GRAPHQL_ENDPOINT_PROD=https://api.yourapp.com/graphql

# Auth0
AUTH0_DOMAIN_DEV=dev-yourapp.auth0.com
AUTH0_CLIENT_ID_DEV=your-dev-client-id
AUTH0_DOMAIN_STAGING=staging-yourapp.auth0.com
AUTH0_CLIENT_ID_STAGING=your-staging-client-id
AUTH0_DOMAIN_PROD=yourapp.auth0.com
AUTH0_CLIENT_ID_PROD=your-prod-client-id

# Feature Flags
ENABLE_HEALTH_SYNC=true
ENABLE_ANALYTICS=false
SHOW_DEBUG_INFO=true
```### Health Service (Platform Abstraction)

Crea `lib/services/health/health_service.dart`:

```dart
import 'package:health/health.dart';
import 'package:permission_handler/permission_handler.dart';
import '../../core/enums/health_data_type.dart';
import '../../data/models/health/health_metric.dart';

class HealthService {
  static final HealthService _instance = HealthService._internal();
  factory HealthService() => _instance;
  HealthService._internal();

  final Health _health = Health();

  // Health data types we want to access
  static const List<HealthDataType> _healthDataTypes = [
    HealthDataType.STEPS,
    HealthDataType.ACTIVE_ENERGY_BURNED,
    HealthDataType.DISTANCE_WALKING_RUNNING,
    HealthDataType.HEART_RATE,
    HealthDataType.WEIGHT,
    HealthDataType.WORKOUT,
  ];

  // Request permissions for health data
  Future<bool> requestPermissions() async {
    try {
      final hasPermissions = await _health.hasPermissions(_healthDataTypes);
      if (!hasPermissions!) {
        final granted = await _health.requestAuthorization(_healthDataTypes);
        return granted;
      }
      return true;
    } catch (e) {
      print('Error requesting health permissions: $e');
      return false;
    }
  }

  // Get health data for a specific date range
  Future<List<HealthMetric>> getHealthData({
    required DateTime from,
    required DateTime to,
  }) async {
    try {
      final hasPermissions = await requestPermissions();
      if (!hasPermissions) {
        throw Exception('Health permissions not granted');
      }

      final healthData = await _health.getHealthDataFromTypes(
        from,
        to,
        _healthDataTypes,
      );

      return healthData.map((data) => HealthMetric.fromHealthData(data)).toList();
    } catch (e) {
      print('Error fetching health data: $e');
      rethrow;
    }
  }

  // Get today's health summary
  Future<Map<String, dynamic>> getTodaysSummary() async {
    final now = DateTime.now();
    final startOfDay = DateTime(now.year, now.month, now.day);
    
    try {
      final healthData = await getHealthData(
        from: startOfDay,
        to: now,
      );

      // Aggregate data by type
      final summary = <String, dynamic>{};
      
      for (final metric in healthData) {
        switch (metric.type) {
          case HealthDataType.STEPS:
            summary['steps'] = (summary['steps'] ?? 0) + (metric.value as int);
            break;
          case HealthDataType.ACTIVE_ENERGY_BURNED:
            summary['calories'] = (summary['calories'] ?? 0.0) + (metric.value as double);
            break;
          case HealthDataType.DISTANCE_WALKING_RUNNING:
            summary['distance'] = (summary['distance'] ?? 0.0) + (metric.value as double);
            break;
          // Add more cases as needed
        }
      }

      summary['lastUpdated'] = now.toIso8601String();
      return summary;
    } catch (e) {
      print('Error getting today\'s summary: $e');
      rethrow;
    }
  }

  // Background sync method
  Future<bool> syncHealthDataToServer() async {
    try {
      final yesterday = DateTime.now().subtract(const Duration(days: 1));
      final today = DateTime.now();
      
      final healthData = await getHealthData(from: yesterday, to: today);
      
      if (healthData.isEmpty) return true;
      
      // Convert to GraphQL format
      final healthMetrics = healthData.map((metric) => {
        'type': metric.type.name,
        'value': metric.value,
        'timestamp': metric.timestamp.toIso8601String(),
        'unit': metric.unit,
      }).toList();

      // Send to server via GraphQL
      final graphqlService = GraphQLService();
      final result = await graphqlService.syncHealthData({
        'metrics': healthMetrics,
        'syncTimestamp': DateTime.now().toIso8601String(),
      });

      return !result.hasException;
    } catch (e) {
      print('Error syncing health data: $e');
      return false;
    }
  }

  // Check if health data is available on this device
  Future<bool> isHealthDataAvailable() async {
    return await _health.isDataTypeAvailable(HealthDataType.STEPS);
  }
}
```

### Background Sync Service

Crea `lib/services/background/background_sync_service.dart`:

```dart
import 'dart:async';
import 'package:flutter/foundation.dart';
import '../health/health_service.dart';
import '../../config/app_config.dart';

class BackgroundSyncService {
  static final BackgroundSyncService _instance = BackgroundSyncService._internal();
  factory BackgroundSyncService() => _instance;
  BackgroundSyncService._internal();

  Timer? _syncTimer;
  final HealthService _healthService = HealthService();
  bool _isSyncing = false;

  // Start periodic background sync
  void startPeriodicSync() {
    if (!AppConfig.enableHealthSync) return;

    _syncTimer?.cancel();
    _syncTimer = Timer.periodic(AppConfig.syncInterval, (_) async {
      if (!_isSyncing) {
        await _performSync();
      }
    });
  }

  // Stop background sync
  void stopPeriodicSync() {
    _syncTimer?.cancel();
    _syncTimer = null;
  }

  // Manual sync trigger
  Future<bool> triggerSync() async {
    if (_isSyncing) return false;
    return await _performSync();
  }

  Future<bool> _performSync() async {
    if (_isSyncing) return false;
    
    _isSyncing = true;
    try {
      debugPrint('Starting health data sync...');
      final success = await _healthService.syncHealthDataToServer();
      debugPrint('Health data sync ${success ? 'completed' : 'failed'}');
      return success;
    } catch (e) {
      debugPrint('Health data sync error: $e');
      return false;
    } finally {
      _isSyncing = false;
    }
  }

  bool get isSyncing => _isSyncing;

  void dispose() {
    _syncTimer?.cancel();
  }
}
```# Flutter Health & Fitness App - Complete Architecture Guide

Guida completa per sviluppare un'app Flutter con GraphQL, Auth0, HealthKit/GoogleFit integration. Progettata per team junior con focus su scalabilità e manutenibilità.

## 1. Setup Iniziale e Dipendenze

### Core Dependencies

Aggiungi tutte le dipendenze necessarie al tuo `pubspec.yaml`:

```yaml
dependencies:
  flutter:
    sdk: flutter
  
  # GraphQL
  graphql_flutter: ^5.1.2
  
  # Authentication
  auth0_flutter: ^1.4.0
  flutter_secure_storage: ^9.0.0
  
  # Health Data Integration
  health: ^9.0.0              # HealthKit (iOS) + Google Fit (Android)
  permission_handler: ^11.0.2
  
  # Navigation & State Management  
  go_router: ^12.1.1
  flutter_riverpod: ^2.4.9
  
  # Local Storage
  hive_flutter: ^1.1.0
  shared_preferences: ^2.2.2
  
  # Utils
  intl: ^0.18.1
  freezed_annotation: ^2.4.1
  json_annotation: ^4.8.1
  
dev_dependencies:
  flutter_test:
    sdk: flutter
  flutter_lints: ^3.0.0
  
  # Code Generation
  graphql_codegen: ^0.13.0
  build_runner: ^2.3.3
  freezed: ^2.4.7
  json_serializable: ^6.7.1
  
  # Testing
  mockito: ^5.4.2
  integration_test:
    sdk: flutter
```

### Permissions Setup

#### Android - `android/app/src/main/AndroidManifest.xml`
```xml
<manifest xmlns:android="http://schemas.android.com/apk/res/android">
    <!-- Health Data Permissions -->
    <uses-permission android:name="android.permission.health.READ_STEPS" />
    <uses-permission android:name="android.permission.health.READ_ACTIVE_CALORIES_BURNED" />
    <uses-permission android:name="android.permission.health.READ_DISTANCE" />
    <uses-permission android:name="android.permission.health.READ_HEART_RATE" />
    
    <!-- Network -->
    <uses-permission android:name="android.permission.INTERNET" />
    <uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />
</manifest>
```

#### iOS - `ios/Runner/Info.plist`
```xml
<key>NSHealthShareUsageDescription</key>
<string>Questa app ha bisogno di accedere ai dati sanitari per tracciare i tuoi progressi</string>
<key>NSHealthUpdateUsageDescription</key>
<string>Questa app vuole aggiornare i tuoi dati sanitari</string>
```

Poi esegui:
```bash
flutter pub get
```

## 2. Architettura del Progetto

### Struttura Directory Completa

```
lib/
├── main.dart
├── app.dart                    # App root widget con providers
├── config/
│   ├── app_config.dart         # Configurazione per dev/prod
│   ├── routes.dart             # Configurazione routing
│   └── theme.dart              # App theme
├── core/
│   ├── constants/
│   │   ├── api_constants.dart
│   │   ├── storage_keys.dart
│   │   └── health_constants.dart
│   ├── enums/
│   │   ├── auth_status.dart
│   │   ├── health_data_type.dart
│   │   └── sync_status.dart
│   ├── errors/
│   │   ├── app_exceptions.dart
│   │   └── error_handler.dart
│   └── utils/
│       ├── date_utils.dart
│       ├── health_utils.dart
│       └── validators.dart
├── data/
│   ├── datasources/
│   │   ├── local/
│   │   │   ├── auth_local_datasource.dart
│   │   │   ├── health_local_datasource.dart
│   │   │   └── user_local_datasource.dart
│   │   ├── remote/
│   │   │   ├── auth_remote_datasource.dart
│   │   │   ├── graphql_datasource.dart
│   │   │   ├── health_remote_datasource.dart
│   │   │   └── user_remote_datasource.dart
│   │   └── external/
│   │       ├── health_kit_datasource.dart      # iOS HealthKit
│   │       └── google_fit_datasource.dart      # Android GoogleFit
│   ├── models/
│   │   ├── auth/
│   │   │   ├── auth_user.dart
│   │   │   ├── auth_tokens.dart
│   │   │   └── login_request.dart
│   │   ├── health/
│   │   │   ├── health_metric.dart
│   │   │   ├── daily_summary.dart
│   │   │   ├── workout_session.dart
│   │   │   └── health_sync_status.dart
│   │   └── user/
│   │       ├── user.dart
│   │       ├── user_profile.dart
│   │       └── user_preferences.dart
│   └── repositories/
│       ├── auth_repository_impl.dart
│       ├── health_repository_impl.dart
│       └── user_repository_impl.dart
├── domain/
│   ├── entities/
│   │   ├── auth/
│   │   ├── health/
│   │   └── user/
│   ├── repositories/
│   │   ├── auth_repository.dart
│   │   ├── health_repository.dart
│   │   └── user_repository.dart
│   └── usecases/
│       ├── auth/
│       │   ├── login_usecase.dart
│       │   ├── logout_usecase.dart
│       │   ├── register_usecase.dart
│       │   └── refresh_token_usecase.dart
│       ├── health/
│       │   ├── sync_health_data_usecase.dart
│       │   ├── get_daily_summary_usecase.dart
│       │   ├── get_health_trends_usecase.dart
│       │   └── request_health_permissions_usecase.dart
│       └── user/
│           ├── get_user_profile_usecase.dart
│           ├── update_user_profile_usecase.dart
│           └── get_user_statistics_usecase.dart
├── graphql/
│   ├── schema.graphql              # Schema completo
│   ├── fragments/
│   │   ├── user_fragment.graphql
│   │   ├── health_fragment.graphql
│   │   └── statistics_fragment.graphql
│   ├── queries/
│   │   ├── auth/
│   │   │   └── auth_queries.graphql
│   │   ├── health/
│   │   │   ├── health_queries.graphql
│   │   │   └── health_mutations.graphql
│   │   └── users/
│   │       ├── user_queries.graphql
│   │       └── user_mutations.graphql
│   └── generated/                  # Codice auto-generato
├── presentation/
│   ├── providers/                  # Riverpod providers
│   │   ├── auth_provider.dart
│   │   ├── health_provider.dart
│   │   ├── sync_provider.dart
│   │   └── user_provider.dart
│   ├── screens/
│   │   ├── auth/
│   │   │   ├── login_screen.dart
│   │   │   ├── register_screen.dart
│   │   │   └── onboarding_screen.dart
│   │   ├── health/
│   │   │   ├── dashboard_screen.dart
│   │   │   ├── metrics_screen.dart
│   │   │   ├── trends_screen.dart
│   │   │   └── sync_screen.dart
│   │   ├── profile/
│   │   │   ├── profile_screen.dart
│   │   │   ├── settings_screen.dart
│   │   │   └── statistics_screen.dart
│   │   └── common/
│   │       ├── splash_screen.dart
│   │       └── error_screen.dart
│   ├── widgets/
│   │   ├── common/
│   │   │   ├── custom_app_bar.dart
│   │   │   ├── loading_widget.dart
│   │   │   ├── error_widget.dart
│   │   │   └── permission_widget.dart
│   │   ├── auth/
│   │   │   ├── auth_form.dart
│   │   │   ├── social_login_buttons.dart
│   │   │   └── auth_state_handler.dart
│   │   ├── health/
│   │   │   ├── health_metric_card.dart
│   │   │   ├── health_chart.dart
│   │   │   ├── sync_status_indicator.dart
│   │   │   └── daily_summary_widget.dart
│   │   └── charts/
│   │       ├── line_chart_widget.dart
│   │       ├── bar_chart_widget.dart
│   │       └── progress_chart_widget.dart
│   └── navigation/
│       ├── app_router.dart
│       ├── route_guards.dart
│       └── navigation_observer.dart
└── services/
    ├── auth/
    │   ├── auth0_service.dart          # Auth0 integration
    │   └── token_service.dart          # Token management
    ├── graphql/
    │   ├── graphql_service.dart        # GraphQL client
    │   ├── graphql_interceptor.dart    # Auth interceptor
    │   └── offline_service.dart        # Offline caching
    ├── health/
    │   ├── health_service.dart         # Health platform abstraction
    │   ├── health_sync_service.dart    # Background sync
    │   └── health_permissions_service.dart
    ├── storage/
    │   ├── secure_storage_service.dart # Token/credential storage
    │   └── local_storage_service.dart  # App preferences
    └── background/
        ├── background_sync_service.dart
        └── notification_service.dart
```

### Principi Architetturali

**Clean Architecture + Feature-First Structure**
- **Domain Layer**: Business logic pura, senza dipendenze Flutter
- **Data Layer**: Implementazioni concrete, API calls, local storage  
- **Presentation Layer**: UI + State Management con Riverpod
- **Services**: Servizi di infrastruttura condivisi

**Separazione delle responsabilità**
- Ogni feature ha i suoi use cases, repository, e modelli
- Servizi condivisi per funzionalità cross-cutting
- GraphQL code generation per type safety
- Dependency injection con Riverpod

## 3. Configurazione Multi-Ambiente

### App Configuration

Crea `lib/config/app_config.dart`:

```dart
import 'package:flutter/foundation.dart';

enum Environment { development, staging, production }

class AppConfig {
  static Environment get environment {
    if (kDebugMode) return Environment.development;
    return const bool.fromEnvironment('STAGING') 
        ? Environment.staging 
        : Environment.production;
  }

  // GraphQL Endpoints
  static String get graphqlEndpoint {
    switch (environment) {
      case Environment.development:
        return 'http://localhost:4000/graphql';
      case Environment.staging:
        return 'https://staging-api.yourapp.com/graphql';
      case Environment.production:
        return 'https://api.yourapp.com/graphql';
    }
  }

  // Auth0 Configuration
  static String get auth0Domain {
    switch (environment) {
      case Environment.development:
        return 'dev-yourapp.auth0.com';
      case Environment.staging:
        return 'staging-yourapp.auth0.com';
      case Environment.production:
        return 'yourapp.auth0.com';
    }
  }

  static String get auth0ClientId {
    switch (environment) {
      case Environment.development:
        return 'your-dev-client-id';
      case Environment.staging:
        return 'your-staging-client-id';
      case Environment.production:
        return 'your-prod-client-id';
    }
  }

  // Feature Flags
  static bool get enableHealthSync => environment != Environment.development;
  static bool get enableAnalytics => environment == Environment.production;
  static bool get showDebugInfo => environment == Environment.development;

  // Health Data Sync Intervals
  static Duration get syncInterval {
    switch (environment) {
      case Environment.development:
        return const Duration(minutes: 5);  // Più frequente per testing
      case Environment.staging:
      case Environment.production:
        return const Duration(hours: 1);    // Normale per prod
    }
  }
}
```

## 4. Servizi Core

### Auth0 Service

Crea `lib/services/auth/auth0_service.dart`:

```dart
import 'package:auth0_flutter/auth0_flutter.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import '../../config/app_config.dart';
import '../../core/constants/storage_keys.dart';

class Auth0Service {
  static final Auth0Service _instance = Auth0Service._internal();
  factory Auth0Service() => _instance;
  Auth0Service._internal();

  late final Auth0 _auth0;
  final _secureStorage = const FlutterSecureStorage();

  void initialize() {
    _auth0 = Auth0(
      AppConfig.auth0Domain,
      AppConfig.auth0ClientId,
    );
  }

  // Login methods
  Future<Credentials?> loginWithEmailPassword(String email, String password) async {
    try {
      final credentials = await _auth0
          .authentication
          .login(usernameOrEmail: email, password: password);
      
      await _storeCredentials(credentials);
      return credentials;
    } catch (e) {
      rethrow;
    }
  }

  Future<Credentials?> loginWithSocial() async {
    try {
      final credentials = await _auth0
          .webAuthentication(scheme: 'yourapp')
          .login();
      
      await _storeCredentials(credentials);
      return credentials;
    } catch (e) {
      rethrow;
    }
  }

  // Registration
  Future<void> signUp(String email, String password, String name) async {
    try {
      await _auth0.authentication.signUp(
        email: email,
        password: password,
        connection: 'Username-Password-Authentication',
        userMetadata: {'name': name},
      );
    } catch (e) {
      rethrow;
    }
  }

  // Token management
  Future<String?> getValidAccessToken() async {
    try {
      final storedCredentials = await _getStoredCredentials();
      if (storedCredentials == null) return null;

      // Check if token needs refresh
      if (_needsRefresh(storedCredentials)) {
        final newCredentials = await _auth0
            .authentication
            .renewCredentials(refreshToken: storedCredentials.refreshToken);
        
        await _storeCredentials(newCredentials);
        return newCredentials.accessToken;
      }

      return storedCredentials.accessToken;
    } catch (e) {
      return null;
    }
  }

  Future<void> logout() async {
    try {
      await _auth0
          .webAuthentication(scheme: 'yourapp')
          .logout();
      
      await _clearStoredCredentials();
    } catch (e) {
      rethrow;
    }
  }

  // Private methods
  Future<void> _storeCredentials(Credentials credentials) async {
    await _secureStorage.write(
      key: StorageKeys.accessToken,
      value: credentials.accessToken,
    );
    if (credentials.refreshToken != null) {
      await _secureStorage.write(
        key: StorageKeys.refreshToken,
        value: credentials.refreshToken!,
      );
    }
  }

  Future<Credentials?> _getStoredCredentials() async {
    final accessToken = await _secureStorage.read(key: StorageKeys.accessToken);
    final refreshToken = await _secureStorage.read(key: StorageKeys.refreshToken);
    
    if (accessToken == null) return null;
    
    return Credentials(
      accessToken: accessToken,
      refreshToken: refreshToken,
    );
  }

  bool _needsRefresh(Credentials credentials) {
    // Implement JWT expiration check
    return false; // Simplified for example
  }

  Future<void> _clearStoredCredentials() async {
    await _secureStorage.delete(key: StorageKeys.accessToken);
    await _secureStorage.delete(key: StorageKeys.refreshToken);
  }
}
```

### GraphQL Service con Auth Integration

Crea `lib/services/graphql/graphql_service.dart`:

```dart
import 'package:flutter/material.dart';
import 'package:graphql_flutter/graphql_flutter.dart';
import '../../config/app_config.dart';
import '../auth/auth0_service.dart';

class GraphQLService {
  static final GraphQLService _instance = GraphQLService._internal();
  factory GraphQLService() => _instance;
  GraphQLService._internal();

  GraphQLClient? _client;
  final Auth0Service _authService = Auth0Service();

  GraphQLClient get client {
    if (_client == null) {
      final httpLink = HttpLink(AppConfig.graphqlEndpoint);
      
      // Auth interceptor per aggiungere token automaticamente
      final authLink = AuthLink(
        getToken: () async {
          final token = await _authService.getValidAccessToken();
          return token != null ? 'Bearer $token' : null;
        },
      );

      // Error handling link
      final errorLink = ErrorLink(
        errorHandler: (context, error) {
          if (error.linkException is NetworkException) {
            print('Network Error: ${error.linkException}');
          }
          
          // Handle GraphQL errors
          if (error.graphqlErrors.isNotEmpty) {
            for (final err in error.graphqlErrors) {
              if (err.extensions?['code'] == 'UNAUTHENTICATED') {
                // Handle token expiration
                _handleAuthenticationError();
              }
              print('GraphQL Error: ${err.message}');
            }
          }
        },
      );

      final link = Link.from([
        errorLink,
        authLink.concat(httpLink),
      ]);

      _client = GraphQLClient(
        link: link,
        cache: GraphQLCache(
          store: HiveStore(), // Persistent cache
        ),
        defaultPolicies: DefaultPolicies(
          watchQuery: Policies(
            fetchPolicy: FetchPolicy.cacheAndNetwork,
            errorPolicy: ErrorPolicy.all,
            cacheRereadPolicy: CacheRereadPolicy.mergeOptimistic,
          ),
          query: Policies(
            fetchPolicy: FetchPolicy.cacheFirst,
            errorPolicy: ErrorPolicy.all,
          ),
          mutate: Policies(
            fetchPolicy: FetchPolicy.networkOnly,
            errorPolicy: ErrorPolicy.all,
          ),
        ),
      );
    }
    return _client!;
  }

  // Health data specific methods
  Future<QueryResult> syncHealthData(Map<String, dynamic> healthMetrics) async {
    const String mutation = r'''
      mutation SyncHealthData($input: HealthDataInput!) {
        syncHealthData(input: $input) {
          success
          syncedAt
          metrics {
            type
            value
            timestamp
          }
        }
      }
    ''';

    return await client.mutate(
      MutationOptions(
        document: gql(mutation),
        variables: {'input': healthMetrics},
        fetchPolicy: FetchPolicy.networkOnly,
      ),
    );
  }

  Future<QueryResult> getUserHealthStats(String userId, {int days = 30}) async {
    const String query = r'''
      query GetUserHealthStats($userId: ID!, $days: Int!) {
        user(id: $userId) {
          healthStats(days: $days) {
            dailySummaries {
              date
              steps
              caloriesBurned
              distance
              activeMinutes
            }
            trends {
              metric
              trend
              percentage
            }
            goals {
              type
              target
              current
              achieved
            }
          }
        }
      }
    ''';

    return await client.query(
      QueryOptions(
        document: gql(query),
        variables: {'userId': userId, 'days': days},
        fetchPolicy: FetchPolicy.cacheFirst,
      ),
    );
  }

  // User management methods
  Future<QueryResult> updateUserProfile(Map<String, dynamic> profile) async {
    const String mutation = r'''
      mutation UpdateUserProfile($input: UserProfileInput!) {
        updateUserProfile(input: $input) {
          id
          name
          email
          healthGoals {
            steps
            calories
            activeMinutes
          }
          preferences {
            units
            notifications
            syncFrequency
          }
        }
      }
    ''';

    return await client.mutate(
      MutationOptions(
        document: gql(mutation),
        variables: {'input': profile},
      ),
    );
  }

  void _handleAuthenticationError() {
    // Navigate to login or refresh token
    // This would trigger re-authentication flow
  }

  void dispose() {
    _client?.dispose();
    _client = null;
  }
}
```

## 5. Schema GraphQL e Code Generation

### Schema Completo

Crea `lib/graphql/schema.graphql`:

```graphql
# User Types
type User {
  id: ID!
  email: String!
  name: String!
  avatar: String
  healthProfile: HealthProfile
  healthStats(days: Int = 30): HealthStats
  createdAt: DateTime!
  updatedAt: DateTime!
}

type HealthProfile {
  id: ID!
  userId: ID!
  goals: HealthGoals!
  preferences: UserPreferences!
  lastSyncAt: DateTime
}

type HealthGoals {
  dailySteps: Int!
  dailyCalories: Int!
  weeklyActiveMinutes: Int!
  weeklyWorkouts: Int!
}

type UserPreferences {
  units: UnitSystem!
  notifications: NotificationSettings!
  syncFrequency: SyncFrequency!
  privacyLevel: PrivacyLevel!
}

# Health Data Types
type HealthStats {
  dailySummaries: [DailySummary!]!
  weeklyTrends: [HealthTrend!]!
  monthlyTrends: [HealthTrend!]!
  achievements: [Achievement!]!
}

type DailySummary {
  date: Date!
  steps: Int!
  caloriesBurned: Float!
  distance: Float!
  activeMinutes: Int!
  workouts: [WorkoutSummary!]!
  heartRate: HeartRateData
}

type WorkoutSummary {
  id: ID!
  type: WorkoutType!
  duration: Int! # minutes
  caloriesBurned: Float!
  startTime: DateTime!
  endTime: DateTime!
}

type HeartRateData {
  average: Int
  minimum: Int
  maximum: Int
  restingRate: Int
}

type HealthTrend {
  metric: HealthMetric!
  trend: TrendDirection!
  percentage: Float!
  period: Period!
}

type Achievement {
  id: ID!
  type: AchievementType!
  title: String!
  description: String!
  earnedAt: DateTime!
  icon: String!
}

# Enums
enum UnitSystem {
  METRIC
  IMPERIAL
}

enum SyncFrequency {
  REAL_TIME
  HOURLY
  DAILY
}

enum PrivacyLevel {
  PUBLIC
  FRIENDS
  PRIVATE
}

enum WorkoutType {
  RUNNING
  WALKING
  CYCLING
  SWIMMING
  STRENGTH_TRAINING
  YOGA
  OTHER
}

enum HealthMetric {
  STEPS
  CALORIES
  DISTANCE
  ACTIVE_MINUTES
  HEART_RATE
  WEIGHT
}

enum TrendDirection {
  UP
  DOWN
  STABLE
}

enum Period {
  WEEKLY
  MONTHLY
  QUARTERLY
}

enum AchievementType {
  STEP_MILESTONE
  CALORIE_MILESTONE
  STREAK
  WORKOUT_MILESTONE
  PERSONAL_BEST
}

# Input Types
input CreateUserInput {
  email: String!
  name: String!
  healthGoals: HealthGoalsInput
}

input HealthGoalsInput {
  dailySteps: Int = 10000
  dailyCalories: Int = 2000
  weeklyActiveMinutes: Int = 150
  weeklyWorkouts: Int = 3
}

input UserPreferencesInput {
  units: UnitSystem = METRIC
  notifications: NotificationSettingsInput
  syncFrequency: SyncFrequency = HOURLY
  privacyLevel: PrivacyLevel = PRIVATE
}

input NotificationSettingsInput {
  goalReminders: Boolean = true
  achievementAlerts: Boolean = true
  weeklyReports: Boolean = true
  syncStatus: Boolean = false
}

input HealthDataInput {
  metrics: [HealthMetricInput!]!
  syncTimestamp: DateTime!
}

input HealthMetricInput {
  type: String!
  value: Float!
  timestamp: DateTime!
  unit: String!
}

input UpdateUserProfileInput {
  name: String
  healthGoals: HealthGoalsInput
  preferences: UserPreferencesInput
}

# Custom Scalars
scalar DateTime
scalar Date

# Root Types
type Query {
  # User queries
  me: User
  user(id: ID!): User
  
  # Health queries
  myHealthStats(days: Int = 30): HealthStats
  healthSummary(date: Date!): DailySummary
  achievements: [Achievement!]!
}

type Mutation {
  # Auth mutations (handled by Auth0, but we track user creation)
  createUserProfile(input: CreateUserInput!): User!
  updateUserProfile(input: UpdateUserProfileInput!): User!
  deleteUserAccount: Boolean!
  
  # Health data mutations
  syncHealthData(input: HealthDataInput!): HealthSyncResult!
  updateHealthGoals(input: HealthGoalsInput!): HealthProfile!
  updatePreferences(input: UserPreferencesInput!): HealthProfile!
  
  # Manual data entry
  addWorkout(input: WorkoutInput!): WorkoutSummary!
  addWeightEntry(weight: Float!, date: Date!): Boolean!
}

type HealthSyncResult {
  success: Boolean!
  syncedAt: DateTime!
  metricsProcessed: Int!
  errors: [String!]!
}

input WorkoutInput {
  type: WorkoutType!
  duration: Int!
  caloriesBurned: Float
  startTime: DateTime!
  notes: String
}

type Subscription {
  healthDataUpdated(userId: ID!): DailySummary!
  syncStatusChanged(userId: ID!): SyncStatus!
}

type SyncStatus {
  isActive: Boolean!
  lastSyncAt: DateTime
  nextSyncAt: DateTime
  status: String!
}
```

### Fragments per Code Generation

Crea `lib/graphql/fragments/user_fragment.graphql`:

```graphql
fragment UserBasic on User {
  id
  email
  name
  avatar
  createdAt
}

fragment UserComplete on User {
  ...UserBasic
  healthProfile {
    id
    goals {
      dailySteps
      dailyCalories
      weeklyActiveMinutes
      weeklyWorkouts
    }
    preferences {
      units
      syncFrequency
      privacyLevel
      notifications {
        goalReminders
        achievementAlerts
        weeklyReports
        syncStatus
      }
    }
    lastSyncAt
  }
}
```

Crea `lib/graphql/fragments/health_fragment.graphql`:

```graphql
fragment DailySummaryFragment on DailySummary {
  date
  steps
  caloriesBurned
  distance
  activeMinutes
  heartRate {
    average
    minimum
    maximum
    restingRate
  }
  workouts {
    id
    type
    duration
    caloriesBurned
    startTime
    endTime
  }
}

fragment HealthStatsFragment on HealthStats {
  dailySummaries {
    ...DailySummaryFragment
  }
  weeklyTrends {
    metric
    trend
    percentage
    period
  }
  monthlyTrends {
    metric
    trend
    percentage
    period
  }
  achievements {
    id
    type
    title
    description
    earnedAt
    icon
  }
}
```

### Query Files

Crea `lib/graphql/queries/auth/auth_queries.graphql`:

```graphql
#import "../../fragments/user_fragment.graphql"

query GetCurrentUser {
  me {
    ...UserComplete
  }
}

mutation CreateUserProfile($input: CreateUserInput!) {
  createUserProfile(input: $input) {
    ...UserComplete
  }
}

mutation UpdateUserProfile($input: UpdateUserProfileInput!) {
  updateUserProfile(input: $input) {
    ...UserComplete
  }
}
```

Crea `lib/graphql/queries/health/health_queries.graphql`:

```graphql
#import "../../fragments/health_fragment.graphql"

query GetMyHealthStats($days: Int!) {
  myHealthStats(days: $days) {
    ...HealthStatsFragment
  }
}

query GetHealthSummary($date: Date!) {
  healthSummary(date: $date) {
    ...DailySummaryFragment
  }
}

query GetAchievements {
  achievements {
    id
    type
    title
    description
    earnedAt
    icon
  }
}

mutation SyncHealthData($input: HealthDataInput!) {
  syncHealthData(input: $input) {
    success
    syncedAt
    metricsProcessed
    errors
  }
}

mutation UpdateHealthGoals($input: HealthGoalsInput!) {
  updateHealthGoals(input: $input) {
    id
    goals {
      dailySteps
      dailyCalories
      weeklyActiveMinutes
      weeklyWorkouts
    }
  }
}

mutation AddWorkout($input: WorkoutInput!) {
  addWorkout(input: $input) {
    id
    type
    duration
    caloriesBurned
    startTime
    endTime
  }
}

subscription HealthDataUpdated($userId: ID!) {
  healthDataUpdated(userId: $userId) {
    ...DailySummaryFragment
  }
}

subscription SyncStatusChanged($userId: ID!) {
  syncStatusChanged(userId: $userId) {
    isActive
    lastSyncAt
    nextSyncAt
    status
  }
}
```

### Configurazione Build

Aggiorna `build.yaml`:

```yaml
targets:
  $default:
    builders:
      graphql_codegen:
        options:
          schema: "lib/graphql/schema.graphql"
          queries_glob: "lib/graphql/queries/**/*.graphql"
          output: "lib/graphql/generated/"
          scalar_mapping:
            - graphql_type: "DateTime"
              dart_type: "DateTime"
            - graphql_type: "Date"
              dart_type: "DateTime"
          schema_mapping:
            - schema_type: "HealthMetric"
              dart_type: "HealthMetricType"
            - schema_type: "WorkoutType"
              dart_type: "WorkoutType"
          generate_helpers: true
          fragment_imports: true
```

## 6. State Management con Riverpod

### Authentication Provider

Crea `lib/presentation/providers/auth_provider.dart`:

```dart
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:auth0_flutter/auth0_flutter.dart';
import '../../services/auth/auth0_service.dart';
import '../../core/enums/auth_status.dart';
import '../../data/models/auth/auth_user.dart';

// Auth status enum
enum AuthStatus { unknown, authenticated, unauthenticated }

// Auth state class
class AuthState {
  final AuthStatus status;
  final AuthUser? user;
  final String? error;

  const AuthState({
    this.status = AuthStatus.unknown,
    this.user,
    this.error,
  });

  AuthState copyWith({
    AuthStatus? status,
    AuthUser? user,
    String? error,
  }) {
    return AuthState(
      status: status ?? this.status,
      user: user ?? this.user,
      error: error ?? this.error,
    );
  }
}

// Auth provider
class AuthNotifier extends StateNotifier<AuthState> {
  AuthNotifier() : super(const AuthState()) {
    _checkAuthStatus();
  }

  final Auth0Service _authService = Auth0Service();

  Future<void> _checkAuthStatus() async {
    try {
      final token = await _authService.getValidAccessToken();
      if (token != null) {
        // Fetch user data from GraphQL
        final user = await _fetchUserProfile();
        state = state.copyWith(
          status: AuthStatus.authenticated,
          user: user,
        );
      } else {
        state = state.copyWith(status: AuthStatus.unauthenticated);
      }
    } catch (e) {
      state = state.copyWith(
        status: AuthStatus.unauthenticated,
        error: e.toString(),
      );
    }
  }

  Future<bool> login(String email, String password) async {
    try {
      state = state.copyWith(error: null);
      
      final credentials = await _authService.loginWithEmailPassword(email, password);
      if (credentials != null) {
        final user = await _fetchUserProfile();
        state = state.copyWith(
          status: AuthStatus.authenticated,
          user: user,
        );
        return true;
      }
      return false;
    } catch (e) {
      state = state.copyWith(error: e.toString());
      return false;
    }
  }

  Future<bool> loginWithSocial() async {
    try {
      state = state.copyWith(error: null);
      
      final credentials = await _authService.loginWithSocial();
      if (credentials != null) {
        final user = await _fetchUserProfile();
        state = state.copyWith(
          status: AuthStatus.authenticated,
          user: user,
        );
        return true;
      }
      return false;
    } catch (e) {
      state = state.copyWith(error: e.toString());
      return false;
    }
  }

  Future<bool> register(String email, String password, String name) async {
    try {
      state = state.copyWith(error: null);
      
      await _authService.signUp(email, password, name);
      // After successful registration, user needs to verify email
      // and then login
      return true;
    } catch (e) {
      state = state.copyWith(error: e.toString());
      return false;
    }
  }

  Future<void> logout() async {
    try {
      await _authService.logout();
      state = state.copyWith(
        status: AuthStatus.unauthenticated,
        user: null,
      );
    } catch (e) {
      state = state.copyWith(error: e.toString());
    }
  }

  Future<AuthUser?> _fetchUserProfile() async {
    // Implement GraphQL query to get user profile
    // This would use the generated GraphQL client
    // Return parsed AuthUser object
    return null; // Placeholder
  }
}

// Provider exports
final authProvider = StateNotifierProvider<AuthNotifier, AuthState>((ref) {
  return AuthNotifier();
});

// Convenience providers
final authStatusProvider = Provider<AuthStatus>((ref) {
  return ref.watch(authProvider).status;
});

final currentUserProvider = Provider<AuthUser?>((ref) {
  return ref.watch(authProvider).user;
});
```

### Health Data Provider

Crea `lib/presentation/providers/health_provider.dart`:

```dart
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../services/health/health_service.dart';
import '../../data/models/health/daily_summary.dart';
import '../../data/models/health/health_metric.dart';

// Health permissions state
enum HealthPermissionStatus { unknown, granted, denied, restricted }

class HealthState {
  final HealthPermissionStatus permissionStatus;
  final DailySummary? todaysSummary;
  final List<DailySummary> weeklyData;
  final List<HealthMetric> recentMetrics;
  final bool isLoading;
  final String? error;

  const HealthState({
    this.permissionStatus = HealthPermissionStatus.unknown,
    this.todaysSummary,
    this.weeklyData = const [],
    this.recentMetrics = const [],
    this.isLoading = false,
    this.error,
  });

  HealthState copyWith({
    HealthPermissionStatus? permissionStatus,
    DailySummary? todaysSummary,
    List<DailySummary>? weeklyData,
    List<HealthMetric>? recentMetrics,
    bool? isLoading,
    String? error,
  }) {
    return HealthState(
      permissionStatus: permissionStatus ?? this.permissionStatus,
      todaysSummary: todaysSummary ?? this.todaysSummary,
      weeklyData: weeklyData ?? this.weeklyData,
      recentMetrics: recentMetrics ?? this.recentMetrics,
      isLoading: isLoading ?? this.isLoading,
      error: error ?? this.error,
    );
  }
}

class HealthNotifier extends StateNotifier<HealthState> {
  HealthNotifier() : super(const HealthState()) {
    _checkPermissions();
  }

  final HealthService _healthService = HealthService();

  Future<void> _checkPermissions() async {
    try {
      final hasPermissions = await _healthService.requestPermissions();
      state = state.copyWith(
        permissionStatus: hasPermissions 
          ? HealthPermissionStatus.granted 
          : HealthPermissionStatus.denied,
      );

      if (hasPermissions) {
        await refreshHealthData();
      }
    } catch (e) {
      state = state.copyWith(
        permissionStatus: HealthPermissionStatus.restricted,
        error: e.toString(),
      );
    }
  }

  Future<void> requestPermissions() async {
    try {
      state = state.copyWith(isLoading: true, error: null);
      
      final granted = await _healthService.requestPermissions();
      state = state.copyWith(
        permissionStatus: granted 
          ? HealthPermissionStatus.granted 
          : HealthPermissionStatus.denied,
        isLoading: false,
      );

      if (granted) {
        await refreshHealthData();
      }
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
    }
  }

  Future<void> refreshHealthData() async {
    if (state.permissionStatus != HealthPermissionStatus.granted) return;

    try {
      state = state.copyWith(isLoading: true, error: null);

      // Get today's summary
      final todaySummary = await _healthService.getTodaysSummary();
      
      // Get last 7 days data
      final weekData = await _getWeeklyData();
      
      // Get recent metrics
      final recentMetrics = await _getRecentMetrics();

      state = state.copyWith(
        todaysSummary: DailySummary.fromMap(todaySummary),
        weeklyData: weekData,
        recentMetrics: recentMetrics,
        isLoading: false,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
    }
  }

  Future<List<DailySummary>> _getWeeklyData() async {
    final now = DateTime.now();
    final weekAgo = now.subtract(const Duration(days: 7));
    
    final healthData = await _healthService.getHealthData(
      from: weekAgo,
      to: now,
    );

    // Group by day and create daily summaries
    // Implementation would aggregate data by day
    return []; // Placeholder
  }

  Future<List<HealthMetric>> _getRecentMetrics() async {
    final now = DateTime.now();
    final hourAgo = now.subtract(const Duration(hours: 1));
    
    return await _healthService.getHealthData(
      from: hourAgo,
      to: now,
    );
  }

  Future<void> syncToServer() async {
    try {
      state = state.copyWith(isLoading: true, error: null);
      
      final success = await _healthService.syncHealthDataToServer();
      
      if (success) {
        await refreshHealthData();
      } else {
        state = state.copyWith(
          isLoading: false,
          error: 'Sync failed',
        );
      }
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
    }
  }
}

// Provider exports
final healthProvider = StateNotifierProvider<HealthNotifier, HealthState>((ref) {
  return HealthNotifier();
});

// Convenience providers
final healthPermissionProvider = Provider<HealthPermissionStatus>((ref) {
  return ref.watch(healthProvider).permissionStatus;
});

final todaysSummaryProvider = Provider<DailySummary?>((ref) {
  return ref.watch(healthProvider).todaysSummary;
});

final weeklyHealthDataProvider = Provider<List<DailySummary>>((ref) {
  return ref.watch(healthProvider).weeklyData;
});
```

### Sync Provider

Crea `lib/presentation/providers/sync_provider.dart`:

```dart
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../services/background/background_sync_service.dart';
import '../../core/enums/sync_status.dart';

class SyncState {
  final SyncStatus status;
  final DateTime? lastSyncAt;
  final DateTime? nextSyncAt;
  final String? error;
  final bool isManualSyncInProgress;

  const SyncState({
    this.status = SyncStatus.idle,
    this.lastSyncAt,
    this.nextSyncAt,
    this.error,
    this.isManualSyncInProgress = false,
  });

  SyncState copyWith({
    SyncStatus? status,
    DateTime? lastSyncAt,
    DateTime? nextSyncAt,
    String? error,
    bool? isManualSyncInProgress,
  }) {
    return SyncState(
      status: status ?? this.status,
      lastSyncAt: lastSyncAt ?? this.lastSyncAt,
      nextSyncAt: nextSyncAt ?? this.nextSyncAt,
      error: error ?? this.error,
      isManualSyncInProgress: isManualSyncInProgress ?? this.isManualSyncInProgress,
    );
  }
}

class SyncNotifier extends StateNotifier<SyncState> {
  SyncNotifier() : super(const SyncState()) {
    _initializeSync();
  }

  final BackgroundSyncService _syncService = BackgroundSyncService();

  void _initializeSync() {
    _syncService.startPeriodicSync();
    state = state.copyWith(
      status: SyncStatus.active,
      nextSyncAt: DateTime.now().add(const Duration(hours: 1)),
    );
  }

  Future<void> triggerManualSync() async {
    if (state.isManualSyncInProgress) return;

    try {
      state = state.copyWith(
        isManualSyncInProgress: true,
        error: null,
      );

      final success = await _syncService.triggerSync();
      
      state = state.copyWith(
        isManualSyncInProgress: false,
        lastSyncAt: DateTime.now(),
        nextSyncAt: DateTime.now().add(const Duration(hours: 1)),
        status: success ? SyncStatus.completed : SyncStatus.error,
        error: success ? null : 'Manual sync failed',
      );
    } catch (e) {
      state = state.copyWith(
        isManualSyncInProgress: false,
        status: SyncStatus.error,
        error: e.toString(),
      );
    }
  }

  void pauseSync() {
    _syncService.stopPeriodicSync();
    state = state.copyWith(
      status: SyncStatus.paused,
      nextSyncAt: null,
    );
  }

  void resumeSync() {
    _syncService.startPeriodicSync();
    state = state.copyWith(
      status: SyncStatus.active,
      nextSyncAt: DateTime.now().add(const Duration(hours: 1)),
    );
  }

  @override
  void dispose() {
    _syncService.dispose();
    super.dispose();
  }
}

// Provider exports
final syncProvider = StateNotifierProvider<SyncNotifier, SyncState>((ref) {
  return SyncNotifier();
});

final syncStatusProvider = Provider<SyncStatus>((ref) {
  return ref.watch(syncProvider).status;
});

final isSyncingProvider = Provider<bool>((ref) {
  final state = ref.watch(syncProvider);
  return state.isManualSyncInProgress || state.status == SyncStatus.syncing;
});
```

### Esempio: Users Query

Crea `lib/graphql/queries/users.graphql`:

```graphql
query GetUsers($limit: Int, $offset: Int) {
  users(limit: $limit, offset: $offset) {
    id
    name
    email
    avatar
    createdAt
  }
}

query GetUser($id: ID!) {
  user(id: $id) {
    id
    name
    email
    avatar
    bio
    posts {
      id
      title
      content
    }
  }
}

mutation CreateUser($input: CreateUserInput!) {
  createUser(input: $input) {
    id
    name
    email
  }
}
```

## 11. Screen Structure Examples

### Dashboard Screen Structure

Crea `lib/presentation/screens/health/dashboard_screen.dart`:

```dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../providers/health_provider.dart';
import '../../providers/sync_provider.dart';
import '../../widgets/health/daily_summary_widget.dart';
import '../../widgets/health/health_metric_card.dart';
import '../../widgets/health/sync_status_indicator.dart';
import '../../widgets/common/permission_widget.dart';

class DashboardScreen extends ConsumerWidget {
  const DashboardScreen({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final healthState = ref.watch(healthProvider);
    final syncState = ref.watch(syncProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Health Dashboard'),
        actions: [
          SyncStatusIndicator(),
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => ref.read(healthProvider.notifier).refreshHealthData(),
          ),
        ],
      ),
      body: _buildBody(context, ref, healthState, syncState),
    );
  }

  Widget _buildBody(BuildContext context, WidgetRef ref, HealthState healthState, SyncState syncState) {
    // Check permissions first
    if (healthState.permissionStatus != HealthPermissionStatus.granted) {
      return const PermissionWidget();
    }

    if (healthState.isLoading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (healthState.error != null) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.error_outline, size: 64, color: Colors.red),
            SizedBox(height: 16),
            Text('Error: ${healthState.error}'),
            ElevatedButton(
              onPressed: () => ref.read(healthProvider.notifier).refreshHealthData(),
              child: Text('Retry'),
            ),
          ],
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: () => ref.read(healthProvider.notifier).refreshHealthData(),
      child: SingleChildScrollView(
        padding: EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Today's Summary
            if (healthState.todaysSummary != null)
              DailySummaryWidget(summary: healthState.todaysSummary!),
            
            SizedBox(height: 24),
            
            // Health Metrics Grid
            Text(
              'Today\'s Metrics',
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            SizedBox(height: 16),
            
            _buildMetricsGrid(healthState),
            
            SizedBox(height: 24),
            
            // Quick Actions
            Text(
              'Quick Actions',
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            SizedBox(height: 16),
            
            _buildQuickActions(context, ref),
          ],
        ),
      ),
    );
  }

  Widget _buildMetricsGrid(HealthState healthState) {
    final summary = healthState.todaysSummary;
    if (summary == null) return SizedBox.shrink();

    return GridView.count(
      shrinkWrap: true,
      physics: NeverScrollableScrollPhysics(),
      crossAxisCount: 2,
      childAspectRatio: 1.5,
      mainAxisSpacing: 16,
      crossAxisSpacing: 16,
      children: [
        HealthMetricCard(
          title: 'Steps',
          value: '${summary.steps}',
          icon: Icons.directions_walk,
          color: Colors.blue,
        ),
        HealthMetricCard(
          title: 'Calories',
          value: '${summary.caloriesBurned.toInt()}',
          icon: Icons.local_fire_department,
          color: Colors.orange,
        ),
        HealthMetricCard(
          title: 'Distance',
          value: '${(summary.distance / 1000).toStringAsFixed(1)} km',
          icon: Icons.straighten,
          color: Colors.green,
        ),
        HealthMetricCard(
          title: 'Active Minutes',
          value: '${summary.activeMinutes}',
          icon: Icons.timer,
          color: Colors.purple,
        ),
      ],
    );
  }

  Widget _buildQuickActions(BuildContext context, WidgetRef ref) {
    return Column(
      children: [
        ListTile(
          leading: Icon(Icons.analytics),
          title: Text('View Trends'),
          subtitle: Text('See your health trends over time'),
          trailing: Icon(Icons.arrow_forward_ios),
          onTap: () => context.go('/dashboard/trends'),
        ),
        ListTile(
          leading: Icon(Icons.sync),
          title: Text('Sync Health Data'),
          subtitle: Text('Manual sync with health platforms'),
          trailing: Icon(Icons.arrow_forward_ios),
          onTap: () => context.go('/dashboard/sync'),
        ),
        ListTile(
          leading: Icon(Icons.fitness_center),
          title: Text('Log Workout'),
          subtitle: Text('Manually add a workout session'),
          trailing: Icon(Icons.arrow_forward_ios),
          onTap: () => _showWorkoutDialog(context, ref),
        ),
      ],
    );
  }

  void _showWorkoutDialog(BuildContext context, WidgetRef ref) {
    // Show workout logging dialog
  }
}
```

### Login Screen Structure

Crea `lib/presentation/screens/auth/login_screen.dart`:

```dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../providers/auth_provider.dart';
import '../../widgets/auth/auth_form.dart';
import '../../widgets/auth/social_login_buttons.dart';

class LoginScreen extends ConsumerStatefulWidget {
  const LoginScreen({Key? key}) : super(key: key);

  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen> {
  final _formKey = GlobalKey<FormState>();
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  bool _isLoading = false;

  @override
  Widget build(BuildContext context) {
    ref.listen<AuthState>(authProvider, (previous, next) {
      if (next.status == AuthStatus.authenticated) {
        context.go('/dashboard');
      }
      
      if (next.error != null) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(next.error!),
            backgroundColor: Colors.red,
          ),
        );
      }
    });

    return Scaffold(
      body: SafeArea(
        child: Padding(
          padding: EdgeInsets.all(24),
          child: Column(
            children: [
              Expanded(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    // App Logo/Title
                    Icon(
                      Icons.favorite,
                      size: 80,
                      color: Theme.of(context).primaryColor,
                    ),
                    SizedBox(height: 24),
                    Text(
                      'Health Tracker',
                      style: Theme.of(context).textTheme.headlineMedium,
                    ),
                    SizedBox(height: 8),
                    Text(
                      'Track your health journey',
                      style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                        color: Colors.grey[600],
                      ),
                    ),
                    SizedBox(height: 48),
                    
                    // Login Form
                    AuthForm(
                      formKey: _formKey,
                      emailController: _emailController,
                      passwordController: _passwordController,
                      isLoading: _isLoading,
                      onSubmit: _handleLogin,
                    ),
                    
                    SizedBox(height: 24),
                    
                    // Social Login Buttons
                    SocialLoginButtons(
                      onSocialLogin: _handleSocialLogin,
                    ),
                  ],
                ),
              ),
              
              // Register Link
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Text('Don\'t have an account? '),
                  TextButton(
                    onPressed: () => context.go('/register'),
                    child: Text('Sign up'),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  Future<void> _handleLogin() async {
    if (!(_formKey.currentState?.validate() ?? false)) return;

    setState(() => _isLoading = true);
    
    try {
      await ref.read(authProvider.notifier).login(
        _emailController.text.trim(),
        _passwordController.text,
      );
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  Future<void> _handleSocialLogin() async {
    setState(() => _isLoading = true);
    
    try {
      await ref.read(authProvider.notifier).loginWithSocial();
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();
    super.dispose();
  }
}
```

## 12. Testing Strategy

### Unit Tests Structure

```
test/
├── unit/
│   ├── services/
│   │   ├── auth0_service_test.dart
│   │   ├── health_service_test.dart
│   │   └── graphql_service_test.dart
│   ├── providers/
│   │   ├── auth_provider_test.dart
│   │   ├── health_provider_test.dart
│   │   └── sync_provider_test.dart
│   ├── models/
│   │   ├── auth_user_test.dart
│   │   └── health_metric_test.dart
│   └── utils/
│       ├── date_utils_test.dart
│       └── health_utils_test.dart
├── integration/
│   ├── auth_flow_test.dart
│   ├── health_sync_flow_test.dart
│   └── dashboard_flow_test.dart
└── widget/
    ├── auth_form_test.dart
    ├── health_metric_card_test.dart
    └── dashboard_screen_test.dart
```

### Integration Test Example

Crea `integration_test/app_test.dart`:

```dart
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:your_app/main.dart' as app;

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  group('Health App Integration Tests', () {
    testWidgets('Full app flow test', (WidgetTester tester) async {
      app.main();
      await tester.pumpAndSettle();

      // Test login flow
      expect(find.text('Health Tracker'), findsOneWidget);
      
      // Mock successful login
      await tester.enterText(find.byKey(Key('email_field')), 'test@example.com');
      await tester.enterText(find.byKey(Key('password_field')), 'password123');
      await tester.tap(find.byKey(Key('login_button')));
      await tester.pumpAndSettle();

      // Verify dashboard appears
      expect(find.text('Health Dashboard'), findsOneWidget);
      
      // Test health permissions flow
      // (This would require platform channel mocking)
    });
  });
}
```

## 6. Utilizzo nelle UI

### Setup dell'App con GraphQLProvider

Modifica `lib/main.dart`:

```dart
import 'package:flutter/material.dart';
import 'package:graphql_flutter/graphql_flutter.dart';
import 'services/graphql_service.dart';

void main() async {
  await initHiveForFlutter(); // Per il caching
  runApp(MyApp());
}

class MyApp extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return GraphQLProvider(
      client: ValueNotifier(GraphQLService().client),
      child: MaterialApp(
        title: 'Flutter GraphQL Demo',
        home: UsersListPage(),
      ),
    );
  }
}
```

### Widget con Query

Crea `lib/widgets/users_list.dart`:

```dart
import 'package:flutter/material.dart';
import 'package:graphql_flutter/graphql_flutter.dart';

const String GET_USERS = r'''
  query GetUsers($limit: Int) {
    users(limit: $limit) {
      id
      name
      email
      avatar
    }
  }
''';

class UsersListPage extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('Users')),
      body: Query(
        options: QueryOptions(
          document: gql(GET_USERS),
          variables: {'limit': 20},
          pollInterval: Duration(seconds: 10), // Polling opzionale
        ),
        builder: (QueryResult result, {refetch, fetchMore}) {
          // Loading state
          if (result.isLoading) {
            return Center(child: CircularProgressIndicator());
          }

          // Error state
          if (result.hasException) {
            return Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(Icons.error_outline, size: 64, color: Colors.red),
                  SizedBox(height: 16),
                  Text(
                    'Errore: ${result.exception.toString()}',
                    textAlign: TextAlign.center,
                  ),
                  SizedBox(height: 16),
                  ElevatedButton(
                    onPressed: refetch,
                    child: Text('Riprova'),
                  ),
                ],
              ),
            );
          }

          // Success state
          final List users = result.data?['users'] ?? [];

          return RefreshIndicator(
            onRefresh: () async {
              await refetch?.call();
            },
            child: ListView.builder(
              itemCount: users.length,
              itemBuilder: (context, index) {
                final user = users[index];
                return ListTile(
                  leading: CircleAvatar(
                    backgroundImage: user['avatar'] != null 
                      ? NetworkImage(user['avatar']) 
                      : null,
                    child: user['avatar'] == null 
                      ? Text(user['name'][0].toUpperCase()) 
                      : null,
                  ),
                  title: Text(user['name']),
                  subtitle: Text(user['email']),
                  onTap: () => _navigateToUserDetail(context, user['id']),
                );
              },
            ),
          );
        },
      ),
    );
  }

  void _navigateToUserDetail(BuildContext context, String userId) {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => UserDetailPage(userId: userId),
      ),
    );
  }
}
```

### Widget con Mutation

Crea `lib/widgets/create_user_form.dart`:

```dart
import 'package:flutter/material.dart';
import 'package:graphql_flutter/graphql_flutter.dart';

const String CREATE_USER = r'''
  mutation CreateUser($input: CreateUserInput!) {
    createUser(input: $input) {
      id
      name
      email
    }
  }
''';

class CreateUserForm extends StatefulWidget {
  @override
  _CreateUserFormState createState() => _CreateUserFormState();
}

class _CreateUserFormState extends State<CreateUserForm> {
  final _formKey = GlobalKey<FormState>();
  final _nameController = TextEditingController();
  final _emailController = TextEditingController();

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('Nuovo Utente')),
      body: Mutation(
        options: MutationOptions(
          document: gql(CREATE_USER),
          onCompleted: (dynamic resultData) {
            // Successo
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(content: Text('Utente creato con successo!')),
            );
            Navigator.pop(context);
          },
          onError: (OperationException error) {
            // Errore
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(
                content: Text('Errore: ${error.toString()}'),
                backgroundColor: Colors.red,
              ),
            );
          },
        ),
        builder: (RunMutation runMutation, QueryResult? result) {
          return Padding(
            padding: EdgeInsets.all(16.0),
            child: Form(
              key: _formKey,
              child: Column(
                children: [
                  TextFormField(
                    controller: _nameController,
                    decoration: InputDecoration(labelText: 'Nome'),
                    validator: (value) {
                      if (value?.isEmpty ?? true) {
                        return 'Il nome è obbligatorio';
                      }
                      return null;
                    },
                  ),
                  SizedBox(height: 16),
                  TextFormField(
                    controller: _emailController,
                    decoration: InputDecoration(labelText: 'Email'),
                    keyboardType: TextInputType.emailAddress,
                    validator: (value) {
                      if (value?.isEmpty ?? true) {
                        return 'L\'email è obbligatoria';
                      }
                      return null;
                    },
                  ),
                  SizedBox(height: 32),
                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton(
                      onPressed: result?.isLoading == true 
                        ? null 
                        : () => _createUser(runMutation),
                      child: result?.isLoading == true
                        ? SizedBox(
                            height: 20,
                            width: 20,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : Text('Crea Utente'),
                    ),
                  ),
                ],
              ),
            ),
          );
        },
      ),
    );
  }

  void _createUser(RunMutation runMutation) {
    if (_formKey.currentState?.validate() ?? false) {
      runMutation({
        'input': {
          'name': _nameController.text,
          'email': _emailController.text,
        },
      });
    }
  }

  @override
  void dispose() {
    _nameController.dispose();
    _emailController.dispose();
    super.dispose();
  }
}
```

## 7. Best Practices

### Error Handling

```dart
Widget buildErrorWidget(OperationException exception) {
  if (exception.linkException is NetworkException) {
    return ErrorWidget(
      icon: Icons.wifi_off,
      message: 'Controlla la connessione internet',
      onRetry: onRetry,
    );
  } else if (exception.graphqlErrors.isNotEmpty) {
    return ErrorWidget(
      icon: Icons.error,
      message: exception.graphqlErrors.first.message,
      onRetry: onRetry,
    );
  } else {
    return ErrorWidget(
      icon: Icons.error_outline,
      message: 'Errore sconosciuto',
      onRetry: onRetry,
    );
  }
}
```

### Caching Strategy

```dart
// Configurazione cache più avanzata
final client = GraphQLClient(
  link: link,
  cache: GraphQLCache(
    store: HiveStore(), // Persistente
    possibleTypes: {
      'Node': ['User', 'Post', 'Comment']
    },
  ),
  defaultPolicies: DefaultPolicies(
    watchQuery: Policies(
      fetchPolicy: FetchPolicy.cacheAndNetwork,
      errorPolicy: ErrorPolicy.all,
    ),
    query: Policies(
      fetchPolicy: FetchPolicy.cacheFirst,
      errorPolicy: ErrorPolicy.all,
    ),
  ),
);
```

### Ottimizzazioni Performance

```dart
// Usa FetchPolicy appropriata
QueryOptions(
  document: gql(query),
  fetchPolicy: FetchPolicy.cacheFirst, // Per dati che cambiano poco
  // fetchPolicy: FetchPolicy.networkOnly, // Per dati sempre fresh
);

// Implementa pagination
const String GET_USERS_PAGINATED = r'''
  query GetUsers($first: Int!, $after: String) {
    users(first: $first, after: $after) {
      edges {
        node { id name email }
        cursor
      }
      pageInfo {
        hasNextPage
        endCursor
      }
    }
  }
''';
```

## 8. Testing

### Unit Test per Service

```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:mockito/mockito.dart';

void main() {
  group('GraphQL Service Tests', () {
    test('should fetch users successfully', () async {
      // Mock del client
      final mockClient = MockGraphQLClient();
      
      // Setup mock response
      when(mockClient.query(any)).thenAnswer(
        (_) async => QueryResult(
          data: {
            'users': [
              {'id': '1', 'name': 'Test User', 'email': 'test@example.com'}
            ]
          },
          source: QueryResultSource.network,
        ),
      );

      // Test
      final result = await GraphQLService().query(GET_USERS);
      
      expect(result.hasException, false);
      expect(result.data?['users'], isNotNull);
    });
  });
}
```

## 9. Deployment Tips

### Configurazione per Ambiente

```dart
class Config {
  static const String _devEndpoint = 'http://localhost:4000/graphql';
  static const String _prodEndpoint = 'https://api.yourapp.com/graphql';
  
  static String get graphqlEndpoint {
    return kDebugMode ? _devEndpoint : _prodEndpoint;
  }
}
```

### Performance Monitoring

```dart
// Aggiungi logging per monitoraggio
final link = Link.from([
  ErrorLink(
    errorHandler: (context, error) {
      print('GraphQL Error: $error');
      // Invia a servizio di monitoring (es. Sentry)
    },
  ),
  httpLink,
]);
```

## Conclusione

Questo setup ti fornisce una base solida per GraphQL in Flutter. La configurazione è semplice da comprendere per team junior e facilmente estendibile man mano che l'applicazione cresce.

### Next Steps

1. Implementa authentication token refresh
2. Aggiungi subscription per real-time data
3. Ottimizza le query con fragment
4. Implementa offline support con cache persistente

Happy coding! 🚀