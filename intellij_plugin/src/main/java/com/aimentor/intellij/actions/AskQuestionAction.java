package com.aimentor.intellij.actions;

import com.aimentor.intellij.services.AIMentorService;
import com.aimentor.intellij.ui.AIMentorResponseDialog;
import com.intellij.openapi.actionSystem.AnAction;
import com.intellij.openapi.actionSystem.AnActionEvent;
import com.intellij.openapi.actionSystem.CommonDataKeys;
import com.intellij.openapi.editor.Editor;
import com.intellij.openapi.fileTypes.FileType;
import com.intellij.openapi.project.Project;
import com.intellij.openapi.ui.InputValidator;
import com.intellij.openapi.ui.Messages;
import com.intellij.psi.PsiFile;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

/**
 * Action to ask AI Mentor a question about code or current task
 */
public class AskQuestionAction extends AnAction {
    
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
        
        // Get current context
        Editor editor = e.getData(CommonDataKeys.EDITOR);
        PsiFile psiFile = e.getData(CommonDataKeys.PSI_FILE);
        
        String selectedCode = null;
        String fileName = null;
        
        if (editor != null && editor.getSelectionModel().hasSelection()) {
            selectedCode = editor.getSelectionModel().getSelectedText();
        }
        
        if (psiFile != null) {
            fileName = psiFile.getName();
        }
        
        // Get question from user
        String question = Messages.showInputDialog(
            project,
            "What would you like to ask AI Mentor?",
            "Ask AI Mentor",
            Messages.getQuestionIcon(),
            "",
            new InputValidator() {
                @Override
                public boolean checkInput(String inputString) {
                    return inputString != null && !inputString.trim().isEmpty();
                }
                
                @Override
                public boolean canClose(String inputString) {
                    return checkInput(inputString);
                }
            }
        );
        
        if (question != null && !question.trim().isEmpty()) {
            // Show progress and get response
            service.askQuestion(question, selectedCode, fileName)
                .thenAccept(response -> {
                    // Ensure UI updates happen on the EDT
                    com.intellij.openapi.application.ApplicationManager.getApplication().invokeLater(() -> {
                        AIMentorResponseDialog dialog = new AIMentorResponseDialog(
                            project, 
                            "AI Mentor Response", 
                            question, 
                            response,
                            selectedCode
                        );
                        dialog.show();
                    });
                })
                .exceptionally(throwable -> {
                    com.intellij.openapi.application.ApplicationManager.getApplication().invokeLater(() -> {
                        Messages.showErrorDialog(
                            project,
                            "Failed to get response from AI Mentor: " + throwable.getMessage(),
                            "AI Mentor Error"
                        );
                    });
                    return null;
                });
        }
    }
    
    @Override
    public void update(@NotNull AnActionEvent e) {
        Project project = e.getProject();
        e.getPresentation().setEnabled(project != null);
        
        // Update text based on context
        Editor editor = e.getData(CommonDataKeys.EDITOR);
        if (editor != null && editor.getSelectionModel().hasSelection()) {
            e.getPresentation().setText("Ask AI Mentor About Selection");
        } else {
            e.getPresentation().setText("Ask AI Mentor");
        }
    }
}
