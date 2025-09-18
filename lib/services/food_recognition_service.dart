/// Food Recognition Service Abstractions & Fake Implementation
///
/// Responsabilità:
/// - Invia immagine (già caricata / referenziata da uploadId) a backend analyzeMealPhoto
/// - Poll/subscribe stato inference
/// - Restituisce lista candidati e supporta conferma selezioni
/// - Gestisce fallback manuale se inference fallisce
///
/// NOTE: Dipende dal layer GraphQL generato (codegen) non ancora incluso qui.
/// Si lasciano placeholder per i tipi generati.

import 'dart:async';

/// Domain models (semplificati) - in futuro usare quelli generati da GraphQL codegen
class AIInferenceCandidate {
  final String? id; // inferenceItemId
  final String label;
  final double? grams;
  final double confidence; // 0..1
  final bool portionAdjusted;
  final double? originalGrams;
  final double? uncertaintyLow;
  final double? uncertaintyHigh;
  final String? matchFoodItemId;
  final InferenceSource source;

  AIInferenceCandidate({
    required this.id,
    required this.label,
    required this.grams,
    required this.confidence,
    required this.portionAdjusted,
    this.originalGrams,
    this.uncertaintyLow,
    this.uncertaintyHigh,
    this.matchFoodItemId,
    required this.source,
  });
}

enum InferenceSource { barcode, openFoodFacts, internalDb, generic }

enum InferenceStatus { pending, matched, rejected, confirmed, failed }

class AIInferenceSession {
  final String id;
  final InferenceStatus status;
  final List<AIInferenceCandidate> candidates;
  final bool autoFilled;

  AIInferenceSession({
    required this.id,
    required this.status,
    required this.candidates,
    required this.autoFilled,
  });
}

class ConfirmedMealEntry {
  final String id;
  final String foodId;
  final double quantity;
  final String unit;
  ConfirmedMealEntry({
    required this.id,
    required this.foodId,
    required this.quantity,
    required this.unit,
  });
}

abstract class FoodRecognitionService {
  /// Avvia nuova inference da uploadId restituito da un precedente upload immagine.
  Future<AIInferenceSession> analyzeMealPhoto({required String uploadId});

  /// Ritorna stato sessione inference (polling o subscription fallback)
  Future<AIInferenceSession> getInference(String id);

  /// Conferma una o più selezioni; ritorna MealEntry creati.
  Future<List<ConfirmedMealEntry>> confirmSelections({
    required String inferenceId,
    required List<InferenceSelection> selections,
  });

  /// Stream dei delta nutrizionali (per aggiornare ring in real-time).
  Stream<DailyNutritionDelta> dailyDeltaStream(DateTime date);
}

class InferenceSelection {
  final String? inferenceItemId;
  final String foodId;
  final double quantity;
  final String unit;
  InferenceSelection({
    this.inferenceItemId,
    required this.foodId,
    required this.quantity,
    required this.unit,
  });
}

class DailyNutritionDelta {
  final DateTime date;
  final int addedCalories;
  final double addedProteinG;
  final double addedCarbsG;
  final double addedFatG;
  final String? mealEntryId;
  final NutritionDeltaSource source;
  DailyNutritionDelta({
    required this.date,
    required this.addedCalories,
    required this.addedProteinG,
    required this.addedCarbsG,
    required this.addedFatG,
    this.mealEntryId,
    required this.source,
  });
}

enum NutritionDeltaSource { manual, ai, edit, delete }

/// Fake in-memory implementation (per UI prototyping)
class FakeFoodRecognitionService implements FoodRecognitionService {
  final _sessions = <String, AIInferenceSession>{};
  final _deltaControllers = <String, StreamController<DailyNutritionDelta>>{};

  @override
  Future<AIInferenceSession> analyzeMealPhoto({required String uploadId}) async {
    // Simula id
    final id = 'inference_${DateTime.now().millisecondsSinceEpoch}';
    // Crea sessione pending
    final pending = AIInferenceSession(
      id: id,
      status: InferenceStatus.pending,
      candidates: const [],
      autoFilled: false,
    );
    _sessions[id] = pending;

    // Simula elaborazione asincrona
    Future.delayed(const Duration(milliseconds: 600), () {
      final candidates = [
        AIInferenceCandidate(
          id: 'cand1',
          label: 'chicken breast',
          grams: 150,
          confidence: 0.78,
          portionAdjusted: false,
          originalGrams: 150,
          uncertaintyLow: 135,
          uncertaintyHigh: 165,
          matchFoodItemId: 'food_chicken_breast',
          source: InferenceSource.internalDb,
        ),
        AIInferenceCandidate(
          id: 'cand2',
            label: 'mixed salad',
            grams: 80,
            confidence: 0.55,
            portionAdjusted: true,
            originalGrams: 100,
            uncertaintyLow: 60,
            uncertaintyHigh: 110,
            matchFoodItemId: 'food_mixed_salad_generic',
            source: InferenceSource.generic,
        ),
      ];
      _sessions[id] = AIInferenceSession(
        id: id,
        status: InferenceStatus.matched,
        candidates: candidates,
        autoFilled: false,
      );
    });

    return pending;
  }

  @override
  Future<AIInferenceSession> getInference(String id) async {
    // Polling semplice (in reale si userebbe subscription)
    for (var i = 0; i < 10; i++) {
      final s = _sessions[id];
      if (s != null && s.status != InferenceStatus.pending) return s;
      await Future.delayed(const Duration(milliseconds: 150));
    }
    return _sessions[id]!; // potrebbe ancora essere pending
  }

  @override
  Future<List<ConfirmedMealEntry>> confirmSelections({
    required String inferenceId,
    required List<InferenceSelection> selections,
  }) async {
    final session = _sessions[inferenceId];
    if (session == null) throw StateError('Inference not found');

    // Aggiorna stato
    _sessions[inferenceId] = AIInferenceSession(
      id: session.id,
      status: InferenceStatus.confirmed,
      candidates: session.candidates,
      autoFilled: session.autoFilled,
    );

    final entries = <ConfirmedMealEntry>[];
    for (final sel in selections) {
      final entry = ConfirmedMealEntry(
        id: 'meal_${DateTime.now().microsecondsSinceEpoch}',
        foodId: sel.foodId,
        quantity: sel.quantity,
        unit: sel.unit,
      );
      entries.add(entry);
      // Emissione delta simulato (kcal fittizie)
      final controller = _deltaControllers.putIfAbsent(
        _deltaKey(DateTime.now()),
        () => StreamController.broadcast(),
      );
      controller.add(
        DailyNutritionDelta(
          date: DateTime.now(),
          addedCalories: 250,
          addedProteinG: 30,
          addedCarbsG: 5,
          addedFatG: 10,
          mealEntryId: entry.id,
          source: NutritionDeltaSource.ai,
        ),
      );
    }

    return entries;
  }

  @override
  Stream<DailyNutritionDelta> dailyDeltaStream(DateTime date) {
    final key = _deltaKey(date);
    final controller = _deltaControllers.putIfAbsent(
      key,
      () => StreamController.broadcast(),
    );
    return controller.stream;
  }

  String _deltaKey(DateTime d) => '${d.year}-${d.month}-${d.day}';
}
