/// Offline Meal Queue Prototype
///
/// Scopo: accodare richieste di log pasto quando offline o fallisce la mutation,
/// e riprovare il flush quando ritorna connettività o a intervalli esponenziali.
///
/// NOTE DESIGN (MVP):
/// - Persistenza: demandata a Hive (non ancora implementata qui) -> TODO.
/// - Backoff: 1m,5m,15m, fine (configurabile) -> TODO.
/// - Batch flush: inviare al server in blocco per ridurre roundtrip.
/// - Conflitti: se alimento non valido al flush -> convertire in manual entry fallback (TODO logica).
/// - Ottimismo UI: ritorna subito ID locale per aggiornare summary ring.
///
/// Integrazione futura:
/// - Provider Riverpod `mealQueueProvider`.
/// - Mutation GraphQL `logMeal` (batch) ancora da definire nello schema.
///
/// Questo file fornisce solo l'interfaccia di base e un'implementazione volatile in memoria.

import 'dart:async';
import 'package:uuid/uuid.dart';

final _uuid = Uuid();

/// Rappresenta una richiesta locale di logging pasto.
class PendingMealRequest {
  PendingMealRequest({
    required this.localId,
    required this.foodId,
    required this.quantity,
    required this.unit,
    required this.createdAt,
  });

  final String localId; // UUID locale
  final String foodId; // potrebbe essere un id interno o label provvisoria
  final double quantity;
  final String unit; // es. g, ml, porzione
  final DateTime createdAt;

  Map<String, dynamic> toJson() => {
        'localId': localId,
        'foodId': foodId,
        'quantity': quantity,
        'unit': unit,
        'createdAt': createdAt.toIso8601String(),
      };

  static PendingMealRequest fromJson(Map<String, dynamic> json) => PendingMealRequest(
        localId: json['localId'] as String,
        foodId: json['foodId'] as String,
        quantity: (json['quantity'] as num).toDouble(),
        unit: json['unit'] as String,
        createdAt: DateTime.parse(json['createdAt'] as String),
      );
}

/// Stato interno di una entry in coda.
enum MealQueueStatus { pending, syncing, failed }

class MealQueueEntry {
  MealQueueEntry({
    required this.request,
    required this.status,
    this.attempts = 0,
    this.lastError,
  });

  final PendingMealRequest request;
  MealQueueStatus status;
  int attempts;
  String? lastError;
}

/// Interfaccia per l'implementazione della queue (per futura sostituzione con persistenza Hive).
abstract class IMealQueue {
  Stream<List<MealQueueEntry>> watch();
  Future<String> enqueue({
    required String foodId,
    required double quantity,
    required String unit,
  });

  Future<void> flush();
}

/// Implementazione in memoria (volatile). Non persiste dopo riavvio app.
class InMemoryMealQueue implements IMealQueue {
  final List<MealQueueEntry> _entries = [];
  final _controller = StreamController<List<MealQueueEntry>>.broadcast();

  void _emit() => _controller.add(List.unmodifiable(_entries));

  @override
  Stream<List<MealQueueEntry>> watch() => _controller.stream;

  @override
  Future<String> enqueue({
    required String foodId,
    required double quantity,
    required String unit,
  }) async {
    final id = _uuid.v4();
    final req = PendingMealRequest(
      localId: id,
      foodId: foodId,
      quantity: quantity,
      unit: unit,
      createdAt: DateTime.now().toUtc(),
    );
    _entries.add(MealQueueEntry(request: req, status: MealQueueStatus.pending));
    _emit();
    return id;
  }

  @override
  Future<void> flush() async {
    // TODO: integrazione con mutation GraphQL batch logMeal.
    // Per ora simula successo immediato.
    for (final e in _entries) {
      if (e.status == MealQueueStatus.pending || e.status == MealQueueStatus.failed) {
        e.status = MealQueueStatus.syncing;
      }
    }
    _emit();

    await Future.delayed(const Duration(milliseconds: 150));

    for (final e in _entries) {
      if (e.status == MealQueueStatus.syncing) {
        e.status = MealQueueStatus.pending; // rimane pending fino a vera conferma server
        // In futuro: rimuovere o marcare come committed con remoteId.
      }
    }
    _emit();
  }

  void dispose() {
    _controller.close();
  }
}

/// TODO FUTURO:
/// - Adattatore Hive: serializzazione entries + indice per userId.
/// - Politica di retry esponenziale con backoff configurabile.
/// - Deduplicazione richieste identiche ravvicinate.
/// - Merge batch per stesso timestamp minuto.
