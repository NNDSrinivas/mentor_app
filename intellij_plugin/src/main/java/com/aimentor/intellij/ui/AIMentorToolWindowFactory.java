package com.aimentor.intellij.ui;

import com.aimentor.intellij.services.AIMentorService;
import com.intellij.openapi.components.ServiceManager;
import com.intellij.openapi.project.Project;
import com.intellij.openapi.wm.ToolWindow;
import com.intellij.openapi.wm.ToolWindowFactory;
import com.intellij.ui.content.Content;
import com.intellij.ui.content.ContentFactory;
import org.jetbrains.annotations.NotNull;

/**
 * Factory for creating the AI Mentor tool window
 */
public class AIMentorToolWindowFactory implements ToolWindowFactory {
    
    @Override
    public void createToolWindowContent(@NotNull Project project, @NotNull ToolWindow toolWindow) {
        AIMentorService service = ServiceManager.getService(project, AIMentorService.class);
        service.setProject(project);
        
        AIMentorToolWindow aiMentorToolWindow = new AIMentorToolWindow(project, service);
        
        ContentFactory contentFactory = ContentFactory.SERVICE.getInstance();
        Content content = contentFactory.createContent(aiMentorToolWindow.getPanel(), "", false);
        content.setCloseable(false);
        
        toolWindow.getContentManager().addContent(content);
    }
    
    @Override
    public boolean shouldBeAvailable(@NotNull Project project) {
        return true;
    }
}
