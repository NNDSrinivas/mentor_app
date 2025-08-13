package com.aimentor.intellij.actions;

import com.aimentor.intellij.services.AIMentorService;
import com.aimentor.intellij.ui.CodeGenerationDialog;
import com.intellij.openapi.actionSystem.AnAction;
import com.intellij.openapi.actionSystem.AnActionEvent;
import com.intellij.openapi.actionSystem.CommonDataKeys;
import com.intellij.openapi.command.WriteCommandAction;
import com.intellij.openapi.editor.Document;
import com.intellij.openapi.editor.Editor;
import com.intellij.openapi.project.Project;
import com.intellij.openapi.ui.Messages;
import com.intellij.psi.PsiFile;
import org.jetbrains.annotations.NotNull;

/**
 * Action to generate code for a specific task using AI
 */
public class GenerateCodeAction extends AnAction {
    
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
        
        String fileName = null;
        String fileType = null;
        String existingCode = null;
        
        if (psiFile != null) {
            fileName = psiFile.getName();
            fileType = psiFile.getFileType().getName();
        }
        
        if (editor != null) {
            if (editor.getSelectionModel().hasSelection()) {
                existingCode = editor.getSelectionModel().getSelectedText();
            } else {
                existingCode = editor.getDocument().getText();
            }
        }
        
        // Show code generation dialog
        CodeGenerationDialog dialog = new CodeGenerationDialog(project, fileName, fileType, existingCode);
        if (dialog.showAndGet()) {
            String taskDescription = dialog.getTaskDescription();
            String codeStyle = dialog.getCodeStyle();
            boolean includeTests = dialog.shouldIncludeTests();
            boolean replaceSelection = dialog.shouldReplaceSelection();
            
            // Generate code
            service.generateCodeForTask(taskDescription, fileName, fileType, existingCode, codeStyle, includeTests)
                .thenAccept(generatedCode -> {
                    com.intellij.openapi.application.ApplicationManager.getApplication().invokeLater(() -> {
                        if (generatedCode != null && !generatedCode.trim().isEmpty()) {
                            if (editor != null && replaceSelection) {
                                // Insert/replace code in editor
                                WriteCommandAction.runWriteCommandAction(project, () -> {
                                    Document document = editor.getDocument();
                                    if (editor.getSelectionModel().hasSelection()) {
                                        // Replace selection
                                        int start = editor.getSelectionModel().getSelectionStart();
                                        int end = editor.getSelectionModel().getSelectionEnd();
                                        document.replaceString(start, end, generatedCode);
                                    } else {
                                        // Insert at cursor
                                        int offset = editor.getCaretModel().getOffset();
                                        document.insertString(offset, generatedCode);
                                    }
                                });
                            } else {
                                // Show generated code in dialog for review
                                Messages.showInfoMessage(
                                    project,
                                    "Generated code:\n\n" + generatedCode,
                                    "Generated Code"
                                );
                            }
                        } else {
                            Messages.showWarningDialog(
                                project,
                                "No code was generated. Please try with a more specific task description.",
                                "Code Generation"
                            );
                        }
                    });
                })
                .exceptionally(throwable -> {
                    com.intellij.openapi.application.ApplicationManager.getApplication().invokeLater(() -> {
                        Messages.showErrorDialog(
                            project,
                            "Failed to generate code: " + throwable.getMessage(),
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
    }
}
