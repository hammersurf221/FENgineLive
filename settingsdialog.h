#ifndef SETTINGSDIALOG_H
#define SETTINGSDIALOG_H


#include <QDialog>
#include <QSettings>

class QTabWidget;
class QCheckBox;
class QSpinBox;
class QLineEdit;
class QPushButton;
class QComboBox;
class QDialogButtonBox;

class SettingsDialog : public QDialog
{
    Q_OBJECT

public:
    explicit SettingsDialog(QWidget *parent = nullptr);
    ~SettingsDialog() override;

    // Core settings
    void setAnalysisInterval(int interval);
    int analysisInterval() const;
    void setStockfishDepth(int depth);
    int stockfishDepth() const;
    void setStealthModeEnabled(bool enabled);
    bool stealthModeEnabled() const;

    // Board detection
    void setUseAutoBoardDetection(bool use);
    bool useAutoBoardDetection() const;
    void setForceManualRegion(bool force);
    bool forceManualRegion() const;

    // Move automation
    void setAutoMoveWhenReady(bool enable);
    bool autoMoveWhenReady() const;
    void setAutoMoveDelay(int delay);
    int autoMoveDelay() const;

    // Misc
    void setStockfishPath(const QString &path);
    QString stockfishPath() const;
    void setFenModelPath(const QString &path);
    QString fenModelPath() const;
    void setDefaultPlayerColor(const QString &color);
    QString defaultPlayerColor() const;

signals:
    void resetPgnRequested();

private slots:
    void browseStockfish();
    void browseFenModel();
    void resetDefaults();
    void accept() override;

private:
    void loadSettings();
    void saveSettings();

    QTabWidget *tabs;
    QSpinBox *intervalSpinBox;
    QSpinBox *depthSpinBox;
    QCheckBox *stealthCheckBox;

    QCheckBox *autoBoardDetectCheckBox;
    QCheckBox *forceManualRegionCheckBox;
    QCheckBox *autoMoveCheckBox;
    QSpinBox *autoMoveDelaySpinBox;
    QLineEdit *stockfishPathEdit;
    QPushButton *stockfishBrowseButton;
    QLineEdit *fenModelPathEdit;
    QPushButton *fenModelBrowseButton;
    QComboBox *colorComboBox;

    QPushButton *resetButton;
    QDialogButtonBox *buttonBox;

    QSettings settings;
};

#endif // SETTINGSDIALOG_H
