package net.infernodude777.buildermc.item;

import net.minecraft.block.Block;
import net.minecraft.block.BlockState;
import net.minecraft.block.Blocks;
import net.minecraft.component.DataComponentTypes;
import net.minecraft.component.NbtComponent;
import net.minecraft.entity.player.PlayerEntity;
import net.minecraft.item.Item;
import net.minecraft.item.ItemStack;
import net.minecraft.item.ItemUsageContext;
import net.minecraft.sound.SoundCategory;
import net.minecraft.sound.SoundEvents;
import net.minecraft.text.Text;
import net.minecraft.util.ActionResult;
import net.minecraft.util.Hand;
import net.minecraft.util.math.BlockPos;
import net.minecraft.util.math.Direction;
import net.minecraft.world.World;

import java.util.HashSet;
import java.util.Set;

/**
 * The Builder's Wand — right-click to extend a line of blocks from the clicked face.
 *
 * Modes (shift-right-click to cycle):
 *   LINE    → Places a straight line of blocks in the clicked direction
 *   WALL    → Places a flat wall extending from the clicked face (5x5)
 *   FLOOR   → Places a flat floor/ceiling (5x5)
 */
public class BuildersWandItem extends Item {

    private static final int LINE_LENGTH = 8;
    private static final int WALL_RADIUS = 2;
    private static final int FLOOR_RADIUS = 2;

    public enum Mode {
        LINE("Line"),
        WALL("Wall"),
        FLOOR("Floor");

        private final String displayName;
        Mode(String displayName) {
            this.displayName = displayName;
        }
        public String getDisplayName() {
            return displayName;
        }
    }

    public BuildersWandItem(Settings settings) {
        super(settings);
    }

    @Override
    public ActionResult useOnBlock(ItemUsageContext context) {
        World world = context.getWorld();
        PlayerEntity player = context.getPlayer();
        BlockPos clickedPos = context.getBlockPos();
        Direction side = context.getSide();
        Hand hand = context.getHand();

        if (world.isClient || player == null) {
            return ActionResult.SUCCESS;
        }

        // Sneaking cycles modes instead of placing
        if (player.isSneaking()) {
            cycleMode(player, hand);
            return ActionResult.SUCCESS;
        }

        // Get the block to duplicate
        BlockState targetState = world.getBlockState(clickedPos);
        Block targetBlock = targetState.getBlock();

        // Don't duplicate certain blocks
        if (!isValidTarget(targetBlock)) {
            player.sendMessage(Text.translatable("item.buildermc.builders_wand.invalid_target"), true);
            return ActionResult.FAIL;
        }

        // Get current mode from nbt or default to LINE
        Mode mode = getMode(player, hand);
        Set<BlockPos> placePositions = new HashSet<>();

        switch (mode) {
            case LINE -> getLinePositions(clickedPos, side, placePositions);
            case WALL -> getWallPositions(clickedPos, side, placePositions);
            case FLOOR -> getFloorPositions(clickedPos, side, placePositions);
        }

        // Place blocks
        int placed = 0;
        for (BlockPos pos : placePositions) {
            if (canPlace(world, pos, player)) {
                world.setBlockState(pos, targetState);
                placed++;
            }
        }

        if (placed > 0) {
            world.playSound(null, clickedPos, SoundEvents.BLOCK_STONE_PLACE,
                SoundCategory.BLOCKS, 1.0f, 0.8f + world.random.nextFloat() * 0.4f);
            player.sendMessage(
                Text.translatable("item.buildermc.builders_wand.placed", placed, mode.getDisplayName()),
                true
            );
        }

        return ActionResult.SUCCESS;
    }

    // ─── Placement Logic ────────────────────────────────────────────────────

    private void getLinePositions(BlockPos origin, Direction side, Set<BlockPos> results) {
        for (int i = 1; i <= LINE_LENGTH; i++) {
            results.add(origin.offset(side, i));
        }
    }

    private void getWallPositions(BlockPos origin, Direction side, Set<BlockPos> results) {
        Direction.Axis wallAxis;
        if (side.getAxis() == Direction.Axis.Y) {
            wallAxis = Direction.Axis.X;
        } else {
            wallAxis = Direction.Axis.Y;
        }

        Direction right = wallAxis == Direction.Axis.X ? Direction.EAST : Direction.UP;
        Direction up;

        if (side.getAxis() == Direction.Axis.Y) {
            up = side == Direction.UP ? Direction.NORTH : Direction.SOUTH;
        } else {
            up = Direction.UP;
        }

        for (int h = -WALL_RADIUS; h <= WALL_RADIUS; h++) {
            for (int w = -WALL_RADIUS; w <= WALL_RADIUS; w++) {
                BlockPos pos = origin.offset(side, 1)
                    .offset(right, w)
                    .offset(up, h);
                results.add(pos);
            }
        }
    }

    private void getFloorPositions(BlockPos origin, Direction side, Set<BlockPos> results) {
        // Floor extends horizontally from the clicked face
        BlockPos floorOrigin = origin.offset(side);

        for (int x = -FLOOR_RADIUS; x <= FLOOR_RADIUS; x++) {
            for (int z = -FLOOR_RADIUS; z <= FLOOR_RADIUS; z++) {
                BlockPos pos = floorOrigin.add(x, 0, z);
                results.add(pos);
            }
        }
    }

    // ─── Helpers ────────────────────────────────────────────────────────────

    private boolean canPlace(World world, BlockPos pos, PlayerEntity player) {
        if (pos.getY() < world.getBottomY() || pos.getY() >= world.getTopY()) {
            return false;
        }
        BlockState current = world.getBlockState(pos);
        return (current.isAir() || current.isReplaceable())
            && world.getOtherEntities(null, net.minecraft.util.shape.VoxelShapes.fullCube().getBoundingBox().offset(pos)).isEmpty();
    }

    private boolean isValidTarget(Block block) {
        return block != Blocks.AIR
            && block != Blocks.BEDROCK
            && block != Blocks.COMMAND_BLOCK
            && block != Blocks.CHAIN_COMMAND_BLOCK
            && block != Blocks.REPEATING_COMMAND_BLOCK
            && block != Blocks.BARRIER
            && block != Blocks.STRUCTURE_BLOCK
            && block != Blocks.JIGSAW
            && block != Blocks.END_PORTAL
            && block != Blocks.END_PORTAL_FRAME
            && block != Blocks.NETHER_PORTAL;
    }

    // ─── Mode Management ────────────────────────────────────────────────────

    private Mode getMode(PlayerEntity player, Hand hand) {
        var stack = player.getStackInHand(hand);
        var nbt = stack.getOrDefault(DataComponentTypes.CUSTOM_DATA, NbtComponent.DEFAULT);
        String modeStr = nbt.copyNbt().getString("WandMode");
        try {
            return Mode.valueOf(modeStr);
        } catch (IllegalArgumentException e) {
            return Mode.LINE;
        }
    }

    private void cycleMode(PlayerEntity player, Hand hand) {
        var stack = player.getStackInHand(hand);
        Mode current = getMode(player, hand);
        Mode[] modes = Mode.values();
        Mode next = modes[(current.ordinal() + 1) % modes.length];

        var nbt = stack.getOrDefault(DataComponentTypes.CUSTOM_DATA, NbtComponent.DEFAULT);
        var copy = nbt.copyNbt();
        copy.putString("WandMode", next.name());
        stack.set(DataComponentTypes.CUSTOM_DATA, NbtComponent.of(copy));

        player.sendMessage(
            Text.translatable("item.buildermc.builders_wand.mode", next.getDisplayName()),
            true
        );
        player.playSound(SoundEvents.UI_BUTTON_CLICK, SoundCategory.PLAYERS, 0.5f, 1.0f);
    }

    @Override
    public Text getName(ItemStack stack) {
        var nbt = stack.getOrDefault(DataComponentTypes.CUSTOM_DATA, NbtComponent.DEFAULT);
        String modeStr = nbt.copyNbt().getString("WandMode");
        try {
            Mode mode = Mode.valueOf(modeStr);
            return Text.translatable("item.buildermc.builders_wand.mode_name", mode.getDisplayName());
        } catch (IllegalArgumentException e) {
            return super.getName();
        }
    }
}
