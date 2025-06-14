#ifndef BOARDWIDGET_H
#define BOARDWIDGET_H

#include <QMap>
#include <QWidget>
#include <QPixmap>
#include <QColor>
#include "arrowoverlay.h"

class BoardWidget : public QWidget {
  Q_OBJECT

public:
  explicit BoardWidget(QWidget *parent = nullptr);
  void setPositionFromFen(const QString &fen, bool flipped);
  void setArrows(const QList<QPair<QString, QString>> &newArrows);
  void paintEvent(QPaintEvent *event) override;

protected:
  void resizeEvent(QResizeEvent *event) override;

private:

  ArrowOverlay *arrowOverlay = nullptr;
  QMap<QString, QChar> boardPieces;    // key = square like "e4", value = piece char
  QMap<QString, QPixmap> piecePixmaps; // cached piece images
  int cachedPieceSize = -1;
  QString currentFen;
  bool currentFlipped = false;
  QColor lightSquare = QColor(240, 217, 181);
  QColor darkSquare = QColor(181, 136, 99);

  QString squareToKey(int rank, int file) const;
  QPoint squareToPosition(const QString &square, bool flipped) const;
  void parseFen(const QString &fen);
  void preparePiecePixmaps(int size);
  QSize sizeHint() const override;

};

#endif // BOARDWIDGET_H
