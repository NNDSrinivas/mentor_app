package com.aimentor.intellij.actions;

import com.aimentor.intellij.services.AIMentorService;
import com.aimentor.intellij.ui.AIMentorResponseDialog;
import com.intellij.openapi.actionSystem.AnAction;
import com.intellij.openapi.actionSystem.AnActionEvent;
import com.intellij.openapi.actionSystem.CommonDataKeys;
import com.intellij.openapi.application.ApplicationManager;
import com.intellij.openapi.editor.Editor;
import com.intellij.openapi.project.Project;
import com.intellij.openapi.ui.Messages;
import com.intellij.psi.PsiFile;
import org.jetbrains.annotations.NotNull;

/**
 * Action to analyze code for potential improvements and suggestions
 */
public class AnalyzeCodeAction extends AnAction {
    
    @Override
    public void actionPerformed(@NotNull AnActionEvent e) {
        Project project = e.getProject();
        if (project == null) return;
        
        AIMentorService service = project.getService(AIMentorService.class);
        if (service == null) {
            Messages.showErrorDialog(project, "AI Mentor service is unavailable.", "AI Mentor Error");
            return;
        }
        service.setProject(project);
        
        Editor editor = e.getData(CommonDataKeys.EDITOR);
        PsiFile psiFile = e.getData(CommonDataKeys.PSI_FILE);
        
        String codeToAnalyze = null;
        String fileName = null;
    String fileType = null;
        
        if (editor != null && editor.getSelectionModel().hasSelection()) {
            // Analyze selected code
            codeToAnalyze = editor.getSelectionModel().getSelectedText();
            if (codeToAnalyze == null) {
                codeToAnalyze = ""; // guard null
            }
        } else if (editor != null && psiFile != null) {
            // Analyze entire file
            codeToAnalyze = editor.getDocument().getText();
        }
        
        if (psiFile != null) {
            fileName = psiFile.getName();
            fileType = psiFile.getFileType().getName();
        }
        
        if (codeToAnalyze == null || codeToAnalyze.trim().isEmpty()) {
            Messages.showWarningDialog(
                project,
                "No code selected or file opened for analysis.",
                "AI Mentor - Code Analysis"
            );
            return;
        }
        
    // Ensure language hint is non-null (fallback to 'plaintext')
    String language = fileType != null ? fileType : "plaintext";

    // Perform code analysis
    service.analyzeCode(codeToAnalyze, language, fileName)
            .thenAccept(analysis -> {
                ApplicationManager.getApplication().invokeLater(() -> {
                    AIMentorResponseDialog dialog = new AIMentorResponseDialog(
                        project,
                        "Code Analysis Results",
                        "Analysis for: " + (fileName != null ? fileName : "Selected Code"),
                        analysis,
                        codeToAnalyze
                    );
                    dialog.show();
                });
            })
            .exceptionally(throwable -> {
                com.intellij.openapi.application.ApplicationManager.getApplication().invokeLater(() -> {
                    Messages.showErrorDialog(
                        project,
                        "Failed to analyze code: " + throwable.getMessage(),
                        "AI Mentor Error"
                    );
                });
                return null;
            });
    }
    
    @Override
    public void update(@NotNull AnActionEvent e) {
        Project project = e.getProject();
        Editor editor = e.getData(CommonDataKeys.EDITOR);
        PsiFile psiFile = e.getData(CommonDataKeys.PSI_FILE);
        
        boolean hasCode = false;
        if (editor != null) {
            hasCode = editor.getSelectionModel().hasSelection() || 
                     (psiFile != null && editor.getDocument().getTextLength() > 0);
        }
        
        e.getPresentation().setEnabled(project != null && hasCode);
        
        // Update text based on context
        if (editor != null && editor.getSelectionModel().hasSelection()) {
            e.getPresentation().setText("Analyze Selected Code");
        } else {
            e.getPresentation().setText("Analyze Current File");
        }
    }
}
